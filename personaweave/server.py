"""Loopback-only management API. No ambient browser authorization or public listener."""
import base64
import json
import secrets
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit, parse_qs

WEB = Path(__file__).parent/'web'


def server(host, port=0):
    token = secrets.token_urlsafe(32)
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def respond(self, data, status=200, ctype='application/json', filename=None):
            raw = data if isinstance(data, bytes) else json.dumps(data, ensure_ascii=False).encode()
            self.send_response(status)
            self.send_header('Content-Type', ctype+('; charset=utf-8' if ctype.startswith('text/') or ctype == 'application/json' else ''))
            self.send_header('Content-Length', str(len(raw)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Referrer-Policy', 'no-referrer')
            self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; object-src 'none'")
            if filename:
                self.send_header('Content-Disposition', 'attachment; filename="'+filename+'"')
            self.end_headers()
            self.wfile.write(raw)

        def do_GET(self):
            self.dispatch(False)

        def do_POST(self):
            self.dispatch(True)

        def dispatch(self, post):
            parsed = urlsplit(self.path)
            path, query = parsed.path, parse_qs(parsed.query)
            expected = f'127.0.0.1:{self.server.server_port}'
            if self.headers.get('Host') != expected:
                return self.respond({'error': 'Invalid Host'}, 403)
            if path.startswith('/api/'):
                if not secrets.compare_digest(self.headers.get('X-Token', ''), token):
                    return self.respond({'error': 'Unauthorized'}, 403)
                origin = self.headers.get('Origin')
                if origin and origin != 'http://'+expected:
                    return self.respond({'error': 'Invalid Origin'}, 403)
            else:
                assets = {'/': ('index.html', 'text/html'), '/app.js': ('app.js', 'text/javascript'), '/upstream.js': ('upstream.js', 'text/javascript'), '/style.css': ('style.css', 'text/css'), '/logo.svg': ('logo.svg','image/svg+xml'), '/icon.svg': ('icon.svg','image/svg+xml'), '/icon.png': ('icon.png','image/png')}
                if post or path not in assets:
                    return self.respond({}, 404)
                file, typ = assets[path]
                return self.respond((WEB/file).read_bytes(), ctype=typ)
            try:
                data = {}
                if post:
                    size = int(self.headers.get('Content-Length', '0'))
                    if size < 0 or size > 16_000_000:
                        return self.respond({'error': 'Request too large'}, 413)
                    data = json.loads(self.rfile.read(size) or '{}')
                    if not isinstance(data, dict):
                        raise ValueError('Expected object')
                if not post:
                    routes = {'/api/status': host.status, '/api/config': host.config, '/api/characters': host.store.characters,
                              '/api/diagnostics': host.diagnostics, '/api/extensions': host.extensions.list,
                              '/api/astrbot/catalog': lambda: host.astrbot.catalog(query.get('character_id', [''])[0]),
                              '/api/usage': lambda: host.models.report(query.get('days', ['30'])[0]),
                              '/api/events': lambda: host.store.rows('SELECT * FROM events WHERE id>? ORDER BY id DESC LIMIT 100', (int(query.get('after', ['0'])[0]),)),
                              '/api/setup': lambda: self.setup_info()}
                    if path not in routes:
                        return self.respond({}, 404)
                    return self.respond(routes[path]())
                cid = data.get('character_id', '')
                audience = str(data.get('audience') or 'owner')
                if path == '/api/character/export':
                    return self.respond(host.store.export_character(cid, data.get('include_private') is True), ctype='application/zip', filename='PersonaWeave-Character.zip')
                if path == '/api/qq/image':
                    if not host.channel:
                        raise ValueError('请先连接 QQ')
                    image = data.get('image', '')
                    if len(image) > 10_000_000:
                        raise ValueError('图片过大')
                    raw = base64.b64decode(image, validate=True)
                    if not (raw.startswith(b'\x89PNG\r\n\x1a\n') or raw.startswith(b'\xff\xd8\xff')):
                        raise ValueError('仅支持 PNG/JPEG')
                    return self.respond(host.channel.send_image(data['target'], image))
                routes = {
                    '/api/config': lambda: host.configure(data), '/api/character': lambda: host.save_character(data),
                    '/api/character/import': lambda: host.store.import_character(data['data']),
                    '/api/connect': host.connect, '/api/channel/connect': lambda: host.connect_external(data['platform']),
                    '/api/channel/stop': lambda: self.stop_channel(data['platform']),
                    '/api/protocol/configure': host.configure_protocol, '/api/protocol/start': host.start_protocol, '/api/protocol/stop': host.stop_protocol,
                    '/api/install/node': lambda: host.job('node'), '/api/install/dsh': lambda: host.job('dsh'), '/api/install/napcat': lambda: host.job('napcat'),
                    '/api/job': lambda: host.job(data['action']), '/api/console': lambda: host.console(data['kind']),
                    '/api/autostart': lambda: __import__('personaweave.desktop', fromlist=['autostart']).autostart(bool(data['enabled']), host.store.root),
                    '/api/task': lambda: host.submit(cid, 'owner', data['text'], images=self.images(data.get('images', []))),
                    '/api/cancel': lambda: host.cancel(cid), '/api/session/new': lambda: host.new_session(cid, audience),
                    '/api/approve': lambda: host.decide(data['id'], data.get('allow') is True),
                    '/api/create': lambda: host.create_persona(data), '/api/model/test': lambda: host.models.test(data.get('creation') is True),
                    '/api/plugins': lambda: host.plugins(cid, data['action'], data['package']),
                    '/api/catalog/search': lambda: host.extensions.catalog(data['query']),
                    '/api/catalog/inspect': lambda: host.extensions.inspect(data['package']),
                    '/api/extensions/save': lambda: host.extensions.save(data),
                    '/api/extensions/operate': lambda: host.extensions.operate(cid, data['id'], data['action']),
                    '/api/extensions/secret': lambda: host.extensions.secret(data['name'], data['value']),
                    '/api/astrbot/bind': lambda: host.astrbot.bind(data),
                    '/api/astrbot/unbind': lambda: host.astrbot.unbind(cid),
                    '/api/astrbot/operate': lambda: host.astrbot.operate(cid, data['id'], data['action']),
                    '/api/astrbot/bridge': lambda: host.astrbot.bridge(cid, data['url'], data['token']),
                    '/api/astrbot/persona': lambda: host.astrbot.sync_persona(cid),
                    '/api/native/stop': host.stop_native_web,
                    '/api/memory/list': lambda: host.store.memories(cid, audience, data.get('query', '')),
                    '/api/memory/add': lambda: {'id': host.store.add_memory(cid, audience, data['content'], data.get('kind', 'event'))},
                    '/api/memory/edit': lambda: host.store.edit_memory(cid, data['id'], data['content'], audience, data.get('kind', 'event')),
                    '/api/memory/delete': lambda: host.store.write('DELETE FROM memory WHERE id=? AND character_id=?', (data['id'], cid)),
                    '/api/knowledge/list': lambda: host.store.knowledge(cid, audience, data.get('query', '')),
                    '/api/knowledge/add': lambda: host.store.add_knowledge(cid, audience, data['title'], data['content']),
                    '/api/knowledge/delete': lambda: self.delete_knowledge(cid, data['id']),
                    '/api/history': lambda: host.store.history(cid, audience, 100), '/api/backup': host.store.backup,
                }
                if path not in routes:
                    return self.respond({}, 404)
                return self.respond(routes[path]())
            except Exception as e:
                return self.respond({'error': host.redact(str(e))}, 400)

        def images(self, images):
            if not isinstance(images, list) or len(images) > 4:
                raise ValueError('最多附加4张图片')
            accepted = []
            for image in images:
                if image.get('mimeType') not in ('image/png', 'image/jpeg', 'image/webp') or len(image.get('data', '')) > 4_000_000:
                    raise ValueError('图片格式或大小无效')
                raw = base64.b64decode(image['data'], validate=True)
                mime = image['mimeType']
                if not ((mime == 'image/png' and raw.startswith(b'\x89PNG\r\n\x1a\n')) or (mime == 'image/jpeg' and raw.startswith(b'\xff\xd8\xff')) or (mime == 'image/webp' and raw[:4] == b'RIFF' and raw[8:12] == b'WEBP')):
                    raise ValueError('图片内容与格式不符')
                accepted.append({'type': 'image', 'mimeType': mime, 'data': image['data']})
            return accepted

        def delete_knowledge(self, cid, kid):
            host.store.character(cid)
            # Use recorded UUID only, never client-supplied filesystem paths.
            rows = host.store.rows('SELECT id FROM knowledge WHERE id=? AND character_id=?', (kid, cid))
            if rows:
                path = host.store.root/'Characters'/cid/'knowledge'/(rows[0]['id']+'.md')
                path.unlink(missing_ok=True)
                host.store.write('DELETE FROM knowledge WHERE id=? AND character_id=?', (kid, cid))
            return {'ok': True}

        def stop_channel(self, platform):
            channel = host.channels.pop(platform, None)
            if channel:
                channel.close()
            return {'ok': True}

        def setup_info(self):
            c = host.config()
            return {'owner': bool(c['owner']), 'character': bool(c['character_id']), 'protocol': c['protocol'],
                    'runtime_configured': bool(c['model'] and c['runtime_url']), 'creation_configured': bool(c['creation_model'] and c['creation_url']),
                    'data_directory': str(host.store.root), 'schema_version': host.store.get('schema_version'),
                    'steps': ['配置运行及创作 API 并测试', '创建角色并选择默认角色', '安装 Node / DSH', '选择并安装或连接 QQ 协议端', '打开官方控制台扫码', '设置 OneBot WebSocket 和 Token', '绑定主人身份并重新联动', '从主人 QQ 发送任务']}
    httpd = ThreadingHTTPServer(('127.0.0.1', port), Handler)
    httpd.daemon_threads = True
    return httpd, token
