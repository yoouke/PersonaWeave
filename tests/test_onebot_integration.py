"""Authenticated OneBot websocket -> host -> isolated model -> acknowledged reply."""
import asyncio
import json
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
from personaweave.host import Host


class OneBotIntegrationTests(unittest.TestCase):
    def test_event_routing_owner_and_nonowner_reply_ack(self):
        from websockets.asyncio.server import serve
        ready, finished, stop = threading.Event(), threading.Event(), threading.Event()
        messages, ports, failure = [], [], []
        async def handler(ws):
            if ws.request.headers.get('Authorization') != 'Bearer local-onebot-token':
                await ws.close(); return
            event = {'post_type': 'message', 'message_type': 'private', 'self_id': 55555, 'user_id': 12345, 'message_id': 77, 'message': [{'type': 'text', 'data': {'text': '消息通道任务'}}]}
            async for raw in ws:
                req = json.loads(raw)
                if req['action'] == 'get_status':
                    await ws.send(json.dumps({'status': 'ok', 'retcode': 0, 'echo': req['echo'], 'data': {'online': True}}))
                    await ws.send(json.dumps(event))
                    await ws.send(json.dumps(event))  # Duplicate events must not replay work.
                elif req['action'] == 'send_private_msg':
                    messages.append(req['params'])
                    await ws.send(json.dumps({'status': 'ok', 'retcode': 0, 'echo': req['echo'], 'data': {'message_id': 88}}))
                    finished.set()
        async def run():
            try:
                async with serve(handler, '127.0.0.1', 0) as server:
                    ports.append(server.sockets[0].getsockname()[1]); ready.set()
                    while not stop.is_set(): await asyncio.sleep(.05)
            except Exception as e:
                failure.append(str(e)); ready.set()
        thread = threading.Thread(target=lambda: asyncio.run(run()), daemon=True)
        thread.start()
        self.assertTrue(ready.wait(3)); self.assertFalse(failure, failure)
        with tempfile.TemporaryDirectory() as root:
            host = Host(root)
            char = host.store.save_character({'name': '通信测试', 'engine': 'openai'})
            host.configure({'owner': '12345', 'character_id': char['id'], 'onebot_url': f'ws://127.0.0.1:{ports[0]}'})
            try:
                with patch.object(host.vault, 'get', return_value='local-onebot-token'), patch.object(host.models, 'chat', return_value='双向通信验证完成') as model:
                    host.connect()
                    self.assertTrue(finished.wait(10))
                    for _ in range(100):
                        if not host.busy: break
                        time.sleep(.01)
                    self.assertEqual(model.call_count, 1)
                    self.assertEqual(messages[0]['user_id'], 12345)
                    self.assertEqual(messages[0]['message'][0]['data']['text'], '双向通信验证完成')
                    self.assertEqual(next(iter(host.tasks.values()))['state'], 'completed')
                    self.assertTrue(host.channel.logged_in)
            finally:
                host.close(); host.store.db.close(); stop.set(); thread.join(5)
