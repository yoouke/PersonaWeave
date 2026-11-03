"""Communication adapters. Identity comes from authenticated transport events."""
import asyncio
import json
import threading
import time
import uuid
from urllib.parse import urlsplit
from .models import request_json


class OneBot:
    def __init__(self, url, token, receive):
        parsed = urlsplit(url)
        if parsed.scheme not in ('ws', 'wss') or parsed.hostname not in ('127.0.0.1', 'localhost', '::1') or parsed.username or parsed.password:
            raise ValueError('OneBot 必须使用本机 WebSocket 地址')
        self.url, self.token, self.receive = url, token, receive
        self.stop = threading.Event()
        self.online = False
        self.logged_in = None
        self.loop, self.ws = None, None
        self.seen, self.pending = {}, {}
        self.error = ''
        self.thread = None

    def start(self):
        if self.thread and self.thread.is_alive():
            return
        self.thread = threading.Thread(target=lambda: asyncio.run(self.run()), daemon=True)
        self.thread.start()

    def status(self):
        return {'connected': self.online, 'logged_in': self.logged_in, 'error': self.error}

    def message(self, event):
        if event.get('post_type') != 'message' or event.get('message_type') not in ('private', 'group'):
            return
        mid = str(event.get('message_id'))
        now = time.monotonic()
        self.seen = {key: stamp for key, stamp in self.seen.items() if now-stamp < 600}
        if mid in self.seen:
            return
        self.seen[mid] = now
        segments = event.get('message', [])
        text = ''.join(str(s.get('data', {}).get('text', '')) for s in segments if s.get('type') == 'text') if isinstance(segments, list) else str(segments)
        group = str(event.get('group_id') or '')
        # Only addressed group messages enter the host; chat messages remain private by sender scope.
        if group and isinstance(segments, list) and not any(s.get('type') == 'at' and str(s.get('data', {}).get('qq')) == str(event.get('self_id')) for s in segments):
            return
        if text.strip():
            context = {'platform': 'qq', 'group': group, 'reply_target': str(event['user_id'])}
            threading.Thread(target=self.receive, args=(str(event['user_id']), text, context), daemon=True).start()

    async def run(self):
        from websockets.asyncio.client import connect
        self.loop = asyncio.get_running_loop()
        while not self.stop.is_set():
            try:
                async with connect(self.url, additional_headers={'Authorization': 'Bearer '+self.token}, max_size=8*1024*1024, open_timeout=10) as ws:
                    self.ws, self.online, self.error = ws, True, ''
                    await ws.send(json.dumps({'action': 'get_status', 'echo': 'host-status'}))
                    async for raw in ws:
                        event = json.loads(raw)
                        echo = event.get('echo')
                        if echo == 'host-status':
                            self.logged_in = (event.get('data') or {}).get('online')
                        elif echo in self.pending:
                            future = self.pending.pop(echo)
                            if not future.done():
                                future.set_result(event)
                        elif event.get('meta_event_type') == 'heartbeat':
                            self.logged_in = (event.get('status') or {}).get('online')
                        else:
                            self.message(event)
            except Exception:
                if not self.stop.is_set():
                    self.error = 'OneBot 连接中断；请检查协议端、端口及 Token。'
            finally:
                self.online = False
                self.logged_in = None
                for future in list(self.pending.values()):
                    if not future.done():
                        future.set_exception(RuntimeError('OneBot 连接已断开'))
                self.pending.clear()
            if not self.stop.is_set():
                await asyncio.sleep(3)

    async def _call(self, action, params):
        echo = uuid.uuid4().hex
        future = self.loop.create_future()
        self.pending[echo] = future
        try:
            await self.ws.send(json.dumps({'action': action, 'params': params, 'echo': echo}))
            result = await asyncio.wait_for(future, 15)
            if result.get('status') != 'ok' or result.get('retcode', 0) != 0:
                raise RuntimeError('OneBot 操作被协议端拒绝：'+str(result.get('retcode')))
            return result.get('data')
        finally:
            self.pending.pop(echo, None)

    def call(self, action, params):
        if not self.online:
            raise RuntimeError('QQ 通道尚未连接')
        return asyncio.run_coroutine_threadsafe(self._call(action, params), self.loop).result(20)

    def send(self, uid, text, group=''):
        if not self.online:
            raise RuntimeError('QQ 通道尚未连接')
        for offset in range(0, len(text), 1800):
            target = {'group_id': int(group)} if group else {'user_id': int(uid)}
            self.call('send_group_msg' if group else 'send_private_msg', {**target, 'message': [{'type': 'text', 'data': {'text': text[offset:offset+1800]}}]})

    def send_image(self, uid, encoded, group=''):
        target = {'group_id': int(group)} if group else {'user_id': int(uid)}
        return self.call('send_group_msg' if group else 'send_private_msg', {**target, 'message': [{'type': 'image', 'data': {'file': 'base64://'+encoded}}]})

    def close(self):
        self.stop.set()
        if self.ws and self.loop and not self.loop.is_closed():
            asyncio.run_coroutine_threadsafe(self.ws.close(), self.loop)
        if self.thread and self.thread is not threading.current_thread():
            self.thread.join(3)


class Telegram:
    def __init__(self, token, receive):
        if not token or not all(c.isalnum() or c in ':_-' for c in token):
            raise ValueError('请保存有效 Telegram Bot Token')
        self.token, self.receive = token, receive
        self.stop, self.online, self.error = threading.Event(), False, ''

    def start(self):
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()

    def status(self):
        return {'connected': self.online, 'error': self.error}

    def api(self, method, data):
        return request_json('https://api.telegram.org/bot'+self.token+'/'+method, data, timeout=40)

    def run(self):
        offset = None
        while not self.stop.is_set():
            try:
                data = self.api('getUpdates', {'offset': offset, 'timeout': 25, 'allowed_updates': ['message']})
                if not data.get('ok'):
                    raise RuntimeError('Telegram API 返回失败')
                self.online, self.error = True, ''
                for update in data.get('result', []):
                    offset = update['update_id']+1
                    msg = update.get('message', {})
                    sender, chat = msg.get('from', {}), msg.get('chat', {})
                    if sender.get('is_bot') or not msg.get('text') or chat.get('type') != 'private':
                        continue
                    self.receive(str(sender['id']), msg['text'], {'platform': 'telegram', 'reply_target': str(chat['id'])})
            except Exception:
                self.online, self.error = False, 'Telegram 连接失败，请检查 Token、网络或其他轮询实例。'
                self.stop.wait(5)
        self.online = False

    def send(self, uid, text, group=''):
        for offset in range(0, len(text), 3500):
            result = self.api('sendMessage', {'chat_id': uid, 'text': text[offset:offset+3500]})
            if not result.get('ok'):
                raise RuntimeError('Telegram 发送失败')

    def close(self):
        self.stop.set()


class Discord:
    """Discord.py owns Gateway intents, heartbeat, resume and REST rate limits."""
    def __init__(self, token, receive):
        if not token:
            raise ValueError('请保存 Discord Bot Token')
        self.token, self.receive = token, receive
        self.online, self.error = False, ''
        self.loop, self.client = None, None

    def start(self):
        self.thread = threading.Thread(target=lambda: asyncio.run(self.run()), daemon=True)
        self.thread.start()

    def status(self):
        return {'connected': self.online, 'error': self.error}

    async def run(self):
        try:
            import discord
            self.loop = asyncio.get_running_loop()
            intents = discord.Intents.default()
            intents.message_content = True
            self.client = discord.Client(intents=intents)
            @self.client.event
            async def on_ready():
                self.online, self.error = True, ''
            @self.client.event
            async def on_disconnect():
                self.online = False
            @self.client.event
            async def on_message(message):
                if message.author.bot or not message.content or message.guild is not None:
                    return
                threading.Thread(target=self.receive, args=(str(message.author.id), message.content, {'platform': 'discord', 'reply_target': str(message.channel.id)}), daemon=True).start()
            await self.client.start(self.token)
        except Exception:
            self.error = 'Discord 连接失败；检查 Token、Message Content Intent 和网络。'
        finally:
            self.online = False

    def send(self, uid, text, group=''):
        if not self.online:
            raise RuntimeError('Discord 尚未连接')
        async def send():
            import discord
            channel = self.client.get_channel(int(uid)) or await self.client.fetch_channel(int(uid))
            for offset in range(0, len(text), 1800):
                await channel.send(text[offset:offset+1800], allowed_mentions=discord.AllowedMentions.none())
        asyncio.run_coroutine_threadsafe(send(), self.loop).result(30)

    def close(self):
        if self.client and self.loop and not self.loop.is_closed():
            asyncio.run_coroutine_threadsafe(self.client.close(), self.loop)
