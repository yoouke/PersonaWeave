"""Optional real DSH -> local mock OpenAI server. Never calls a paid provider."""
import json
import os
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch
from personaweave.host import Host


@unittest.skipUnless(os.environ.get('PW_DSH_BIN'), 'Set PW_DSH_BIN to a verified DSH CLI JS entry')
class RealDshTests(unittest.TestCase):
    def test_actual_runtime_prompt_response_and_usage(self):
        requests = []
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args): pass
            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                requests.append(body)
                chunks = [
                    {'id': 'chatcmpl-local', 'object': 'chat.completion.chunk', 'created': 1, 'model': 'test-model', 'choices': [{'index': 0, 'delta': {'role': 'assistant', 'content': 'LOCAL-DSH-VERIFIED'}, 'finish_reason': None}]},
                    {'id': 'chatcmpl-local', 'object': 'chat.completion.chunk', 'created': 1, 'model': 'test-model', 'choices': [{'index': 0, 'delta': {}, 'finish_reason': 'stop'}], 'usage': {'prompt_tokens': 100, 'completion_tokens': 5, 'total_tokens': 105}}
                ]
                content = ''.join('data: '+json.dumps(c)+'\n\n' for c in chunks)+'data: [DONE]\n\n'
                raw = content.encode()
                self.send_response(200); self.send_header('Content-Type', 'text/event-stream'); self.send_header('Content-Length', str(len(raw))); self.end_headers(); self.wfile.write(raw)
        api = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        threading.Thread(target=api.serve_forever, daemon=True).start()
        with tempfile.TemporaryDirectory() as root:
            host = Host(root)
            char = host.store.save_character({'name': '集成验证', 'personality': 'PERSONA-ISOLATION-MARKER', 'engine': 'dsh'})
            host.configure({'runtime_url': f'http://127.0.0.1:{api.server_port}/v1', 'provider': 'personaweave', 'model': 'test-model'})
            with patch.object(host.vault, 'get', side_effect=lambda key: 'local-test-key' if key == 'runtime_key' else ''), patch.object(host, 'command', return_value=['node', os.environ['PW_DSH_BIN']]):
                task = host.submit(char['id'], 'owner', 'Respond with a short greeting.')
                try:
                    for _ in range(1800):
                        if char['id'] not in host.busy: break
                        time.sleep(.05)
                    result = host.tasks[task['id']]
                    self.assertEqual(result['state'], 'completed', result)
                    self.assertEqual(result['answer'], 'LOCAL-DSH-VERIFIED')
                    self.assertTrue(requests)
                    self.assertIn('PERSONA-ISOLATION-MARKER', json.dumps(requests))
                    self.assertEqual(host.models.report()['groups'][0]['input_tokens'], 100)
                finally:
                    host.close()
                    for _ in range(100):
                        if not host.busy: break
                        time.sleep(.05)
                    host.store.db.close()
                    api.shutdown(); api.server_close()
