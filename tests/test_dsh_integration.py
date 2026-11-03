"""Optional real DSH -> local mock OpenAI server. Never calls a paid provider."""
import json
import os
import tempfile
import threading
import time
import unittest
import socket
import urllib.request
from http.cookiejar import CookieJar
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch
from personaweave.host import Host


@unittest.skipUnless(os.environ.get('PW_DSH_BIN'), 'Set PW_DSH_BIN to a verified DSH CLI JS entry')
class RealDshTests(unittest.TestCase):
    def test_actual_native_web_profile_serves_official_console(self):
        with tempfile.TemporaryDirectory() as root:
            host = Host(root)
            char = host.store.save_character({'name': '原生插件验证', 'personality': 'WEB-PERSONA'})
            with socket.socket() as port_socket:
                port_socket.bind(('127.0.0.1', 0))
                port = port_socket.getsockname()[1]
            url = f'http://127.0.0.1:{port}'
            host.configure({'character_id': char['id'], 'model': 'test-model', 'dsh_console_url': url})
            with patch.object(host.vault, 'get', return_value='local-test-key'), patch.object(host, 'command', return_value=['node', os.environ['PW_DSH_BIN']]):
                try:
                    host.start_native_web()
                    html = ''
                    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), urllib.request.HTTPCookieProcessor(CookieJar()))
                    last_error = 'waiting for authenticated URL'
                    deadline = time.monotonic()+45
                    while time.monotonic() < deadline:
                        if host.services['dsh-web'].poll() is not None:
                            break
                        authenticated = getattr(host, 'native_web_url', None)
                        if not authenticated:
                            time.sleep(.2)
                            continue
                        try:
                            with opener.open(authenticated, timeout=1) as response:
                                html = response.read().decode()
                            break
                        except OSError as exc:
                            last_error = str(type(exc).__name__)+': '+str(getattr(exc, 'code', 'connection failed'))
                            time.sleep(.2)
                    log = (host.store.root/'logs'/'dsh-web.log').read_text(encoding='utf-8', errors='replace')
                    self.assertIn('DeepSeek Harness', html, last_error+'\n'+log[-4000:])
                    self.assertNotIn(authenticated.split('token=')[1], log)
                    self.assertNotIn('token=', json.dumps(host.config()))
                    self.assertIsNone(host.services['dsh-web'].poll())
                    native_patch = json.loads((host.store.root/'Characters'/char['id']/'config'/'native-web.patch.json').read_text(encoding='utf-8'))
                    self.assertIn('织灵（PersonaWeave）', native_patch[0]['config']['personaPrefix'])
                    self.assertIn('WEB-PERSONA', native_patch[0]['config']['personaPrefix'])
                    self.assertTrue((host.store.root/'Characters'/char['id']/'workspace'/'PERSONAWEAVE_CONTEXT.md').is_file())
                finally:
                    host.close()
                    host.store.db.close()

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
                    self.assertIn('织灵（PersonaWeave）', json.dumps(requests, ensure_ascii=False))
                    self.assertTrue((host.store.root/'Characters'/char['id']/'workspace'/'PERSONAWEAVE_CONTEXT.md').is_file())
                    self.assertEqual(host.models.report()['groups'][0]['input_tokens'], 100)
                finally:
                    host.close()
                    for _ in range(100):
                        if not host.busy: break
                        time.sleep(.05)
                    host.store.db.close()
                    api.shutdown(); api.server_close()
