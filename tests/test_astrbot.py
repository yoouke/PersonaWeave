"""Exercise the real local HTTP boundary, delegation and refusal paths."""
import json
import tempfile
import threading
import unittest
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch
from types import SimpleNamespace
from personaweave.host import Host
from personaweave.astrbot import LocalApi, local_url


class TestVault:
    def __init__(self):
        self.values = {}
    def get(self, name):
        return self.values.get(name, '')
    def set(self, name, value):
        self.values[name] = value


class AstrBotTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.h = Host(self.tmp.name)
        self.h.vault = TestVault()
        self.addCleanup(self.tmp.cleanup)
        self.addCleanup(self.h.store.db.close)
        self.a = self.h.save_character({'name': 'A', 'personality': 'USER-CREATED-PERSONA'})
        self.b = self.h.save_character({'name': 'B'})
        self.h.configure({'owner': '11111', 'character_id': self.a['id'], 'model': 'test'})
        self.calls, self.plugins, self.plugin_conf = [], [], {'custom_existing_setting': 123}
        self.config = {'admins_id': ['11111'], 'platform_settings': {
            'enable_id_white_list': True, 'id_whitelist': ['qq:FriendMessage:11111']},
            'platform': [{'id': 'qq', 'type': 'aiocqhttp', 'enable': True}]}
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def respond(self, data, status=200):
                raw = json.dumps(data).encode()
                self.send_response(status)
                self.send_header('Content-Length', str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

            def dispatch(self):
                body = json.loads(self.rfile.read(int(self.headers.get('Content-Length', '0'))) or '{}')
                owner.calls.append((self.command, self.path, body))
                if self.path == '/api/v1/auth/login':
                    if body != {'username': 'dafeiyu', 'password': 'BACKEND-PASSWORD'}:
                        return self.respond({'status': 'error'}, 401)
                    return self.respond({'data': {'token': 'UPSTREAM-BEARER'}})
                if self.headers.get('Authorization') != 'Bearer UPSTREAM-BEARER':
                    return self.respond({'status': 'error'}, 401)
                if self.path == '/api/v1/plugins' and self.command == 'GET':
                    return self.respond({'data': owner.plugins})
                if self.path == '/api/v1/plugins/install/github':
                    name = body.get('market_plugin_id', body.get('repository', '')).split('/')[-1]
                    owner.plugins.append({'name': name, 'version': 'upstream', 'activated': True})
                elif self.path.endswith('/enabled'):
                    name = self.path.split('/')[-2]
                    for p in owner.plugins:
                        if p['name'] == name:
                            p['activated'] = body['enabled']
                elif self.path == '/api/v1/config-profiles/default':
                    return self.respond({'data': {'config': owner.config}})
                elif self.path.startswith('/api/v1/plugins/config'):
                    if self.command == 'GET':
                        return self.respond({'data': {'config': owner.plugin_conf}})
                    owner.plugin_conf = body['config']
                return self.respond({'status': 'ok'})

            do_GET = do_POST = do_PATCH = do_PUT = do_DELETE = dispatch

        self.s = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        threading.Thread(target=self.s.serve_forever, daemon=True).start()
        self.addCleanup(self.s.server_close)
        self.addCleanup(self.s.shutdown)
        self.url = 'http://127.0.0.1:'+str(self.s.server_port)

    def bind(self, cid=None):
        return self.h.astrbot.bind({'character_id': cid or self.a['id'], 'url': self.url,
                                  'username': 'dafeiyu', 'password': 'BACKEND-PASSWORD'})

    def test_catalog_is_real_not_preinstalled_claim(self):
        self.assertTrue(all(not p['installed'] for p in self.h.astrbot.catalog()['plugins']))
        self.assertEqual(self.calls, [])
        self.bind()
        self.plugins.append({'name': 'astrbot_plugin_livingmemory', 'version': '6.0', 'activated': True})
        result = self.h.astrbot.catalog(self.a['id'])
        self.assertEqual([p['id'] for p in result['plugins'] if p['installed']], ['astrbot_plugin_livingmemory'])
        self.assertNotIn('BACKEND-PASSWORD', json.dumps(self.h.astrbot.bindings()))
        self.assertNotIn('UPSTREAM-BEARER', json.dumps(self.h.config()))
        with self.assertRaises(ValueError):
            self.bind(self.b['id'])

    def test_install_delegates_to_market_and_preserves_existing_data(self):
        self.bind()
        cid = self.a['id']
        self.h.astrbot.operate(cid, 'astrbot_plugin_livingmemory', 'install')
        self.assertIn(('POST', '/api/v1/plugins/install/github', {
            'install_method': 'market', 'market_plugin_id': 'lxfight/astrbot_plugin_livingmemory'}), self.calls)
        self.assertFalse(self.plugins[0]['activated'])
        self.h.astrbot.operate(cid, 'astrbot_plugin_livingmemory', 'install')
        installs = [x for x in self.calls if x[1].endswith('/install/github')]
        self.assertEqual(len(installs), 1)
        self.assertEqual(self.plugin_conf, {'custom_existing_setting': 123})
        self.assertEqual(self.h.store.character(cid)['personality'], 'USER-CREATED-PERSONA')
        self.assertFalse(self.h.maintenance)

    def test_bridge_rejects_shared_admin_or_group_and_never_writes_then(self):
        self.bind()
        for bad in ('admins', 'group'):
            self.config['admins_id'] = ['11111', '22222'] if bad == 'admins' else ['11111']
            self.config['platform_settings']['id_whitelist'] = ['qq:GroupMessage:12345']
            before = len(self.calls)
            with self.assertRaises(ValueError):
                self.h.astrbot.bridge(self.a['id'], 'http://127.0.0.1:3188', 'BRIDGE-TOKEN')
            self.assertFalse(any(m in ('PUT', 'PATCH') for m, _, _ in self.calls[before:]))

    def test_bridge_uses_upstream_config_keeps_custom_fields(self):
        self.bind()
        self.h.astrbot.bridge(self.a['id'], 'http://127.0.0.1:3188', 'BRIDGE-TOKEN')
        self.assertEqual(self.plugin_conf['allow_users'], ['11111'])
        self.assertFalse(self.plugin_conf['private_passthrough'])
        self.assertEqual(self.plugin_conf['custom_existing_setting'], 123)
        self.assertEqual(self.plugin_conf['allow_groups'], [])
        self.assertNotIn('BRIDGE-TOKEN', json.dumps(self.h.astrbot.bindings()))
        with self.assertRaises(ValueError):
            self.h.astrbot.operate(self.a['id'], 'astrbot_plugin_dsh', 'enable')

    def test_existing_gateway_does_not_create_own_qq_bridge(self):
        self.bind()
        with patch('personaweave.host.OneBot', side_effect=AssertionError('must reuse upstream')):
            self.assertTrue(self.h.connect()['ok'])
        with self.assertRaises(ValueError):
            self.h.start_protocol()
        with self.assertRaises(ValueError):
            self.h.configure_protocol()
        with self.assertRaises(ValueError):
            self.h.job('napcat')

    def test_unbind_removes_only_management_link(self):
        self.bind()
        self.plugins.append({'name': 'meme_manager', 'activated': True})
        self.h.astrbot.unbind(self.a['id'])
        self.assertFalse(self.h.astrbot.bindings())
        self.assertFalse(self.h.vault.get('astrbot:'+self.a['id']))
        self.assertEqual(self.plugins[0]['name'], 'meme_manager')
        self.bind(self.b['id'])

    def test_native_beacon_is_scoped_to_owned_character_process(self):
        self.bind()
        cid = self.a['id']
        path = Path(self.tmp.name)/'Characters'/cid/'config'/'dsh'/'astrbot-ingress.json'
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({'kind': 'dsh-astrbot-ingress', 'pid': 54321, 'url': 'http://127.0.0.1:3333', 'token': 'NATIVE-SECRET'}))
        self.h.services['dsh-web'] = SimpleNamespace(pid=54321, poll=lambda: None)
        self.h.native_web_cid = self.b['id']
        with self.assertRaises(ValueError):
            self.h.astrbot.bridge(cid, '', '')
        self.h.native_web_cid = cid
        self.h.astrbot.bridge(cid, '', '')
        self.assertEqual(self.plugin_conf['token'], 'NATIVE-SECRET')
        self.assertEqual(self.plugin_conf['ingress_url'], 'http://127.0.0.1:3333')
        self.h.services.clear()

    def test_persona_sync_reuses_native_api_and_preserves_model_and_platforms(self):
        self.bind()
        self.h.astrbot.sync_persona(self.a['id'])
        created = next(body for method, path, body in self.calls if method == 'POST' and path == '/api/v1/personas')
        self.assertIn('USER-CREATED-PERSONA', created['system_prompt'])
        self.assertEqual(created['persona_id'], 'personaweave-'+self.a['id'])
        saved = next(body['config'] for method, path, body in self.calls if method == 'PUT' and path == '/api/v1/config-profiles/default')
        self.assertEqual(saved['platform'], self.config['platform'])
        self.assertEqual(saved['admins_id'], ['11111'])

    def test_native_plugin_uses_real_cli_web_profile_and_pinned_package(self):
        with patch.object(self.h, 'command', return_value=['dsh']), patch.object(self.h, 'runtime_path', return_value='/runtime'), patch('personaweave.runtime.subprocess.run', return_value=SimpleNamespace(returncode=0)) as run:
            self.h.install_native('image')
        argv = run.call_args.args[0]
        self.assertEqual(argv, ['dsh', 'plugin', '--profile', 'web', 'add', 'dsh-image-gen@0.10.2'])
        self.assertIn(self.a['id'], run.call_args.kwargs['env']['DSH_HOME'])
        self.assertEqual(self.h.extensions.list(), [])

    def test_only_literal_loopback_and_no_credential_redirect(self):
        for url in ('https://example.com:443', 'http://localhost:6185', 'http://secret@127.0.0.1:6185', self.url+'?x=1', self.url+'/api'):
            with self.assertRaises(ValueError):
                local_url(url)
        class Redirect(BaseHTTPRequestHandler):
            def do_POST(self):
                self.send_response(307)
                self.send_header('Location', 'https://example.com/steal')
                self.end_headers()
            def log_message(self, *args):
                pass
        s = ThreadingHTTPServer(('127.0.0.1', 0), Redirect)
        threading.Thread(target=s.serve_forever, daemon=True).start()
        try:
            with self.assertRaises(ValueError):
                LocalApi('http://127.0.0.1:'+str(s.server_port)).login('user', 'PRIVATE')
        finally:
            s.shutdown()
            s.server_close()
