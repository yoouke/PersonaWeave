import json
import secrets
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

WEB=Path(__file__).parent/'web'
def server(host,port=0):
    token=secrets.token_urlsafe(32)
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args): pass
        def respond(self,data,status=200,ctype='application/json'):
            raw=data if isinstance(data,bytes) else json.dumps(data,ensure_ascii=False).encode()
            self.send_response(status); self.send_header('Content-Type',ctype+'; charset=utf-8'); self.send_header('Content-Length',str(len(raw)))
            self.send_header('Cache-Control','no-store'); self.send_header('X-Content-Type-Options','nosniff'); self.send_header('Referrer-Policy','no-referrer')
            self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'")
            self.end_headers(); self.wfile.write(raw)
        def do_GET(self): self.dispatch(False)
        def do_POST(self): self.dispatch(True)
        def dispatch(self,post):
            path=urlsplit(self.path).path
            expected=f'127.0.0.1:{self.server.server_port}'
            if self.headers.get('Host')!=expected: return self.respond({'error':'Invalid Host'},403)
            if path.startswith('/api/'):
                if not secrets.compare_digest(self.headers.get('X-Token',''),token): return self.respond({'error':'Unauthorized'},403)
                origin=self.headers.get('Origin')
                if origin and origin!='http://'+expected: return self.respond({'error':'Invalid Origin'},403)
            else:
                if post: return self.respond({},404)
                assets={'/':('index.html','text/html'),'/app.js':('app.js','text/javascript'),'/style.css':('style.css','text/css')}
                if path not in assets: return self.respond({},404)
                file,typ=assets[path]; return self.respond((WEB/file).read_bytes(),ctype=typ)
            try:
                data={}
                if post:
                    size=int(self.headers.get('Content-Length','0'))
                    if size<0 or size>1048576: return self.respond({'error':'Request too large'},413)
                    data=json.loads(self.rfile.read(size) or '{}')
                    if not isinstance(data,dict): raise ValueError('Expected object')
                if not post:
                    routes={'/api/status':host.status,'/api/config':host.config,'/api/characters':host.store.characters,'/api/diagnostics':host.diagnostics,
                            '/api/events':lambda:host.store.rows('SELECT * FROM events ORDER BY id DESC LIMIT 100')}
                    if path not in routes: return self.respond({},404)
                    return self.respond(routes[path]())
                routes={'/api/config':lambda:host.configure(data),'/api/character':lambda:host.store.save_character(data),'/api/connect':host.connect,'/api/protocol/start':host.start_protocol,'/api/protocol/stop':host.stop_protocol,'/api/install/napcat':lambda:__import__('personaweave.installers',fromlist=['install_napcat']).install_napcat(host.store.root,host.config()['protocol']),
                        '/api/install/dsh':host.install_dsh,'/api/install/node':lambda:__import__('personaweave.installers',fromlist=['install_node']).install_node(host.store.root),'/api/autostart':lambda:__import__('personaweave.desktop',fromlist=['autostart']).autostart(bool(data['enabled'])),'/api/task':lambda:host.submit(data['character_id'],host.config()['owner'] or 'local',data['text']),
                        '/api/cancel':lambda:host.cancel(data['character_id']),'/api/approve':lambda:host.decide(data['id'],bool(data.get('allow'))),
                        '/api/plugins':lambda:host.plugins(data['character_id'],data['action'],data['package']),'/api/create':lambda:host.create_persona(data),
                        '/api/memory/list':lambda:host.store.memories(data['character_id'],host.config()['owner'] or 'local'),
                        '/api/memory/add':lambda:{'id':host.store.add_memory(data['character_id'],host.config()['owner'] or 'local',data['content'])},
                        '/api/memory/delete':lambda:host.store.write('DELETE FROM memory WHERE id=? AND character_id=?',(data['id'],data['character_id']))}
                if path not in routes: return self.respond({},404)
                return self.respond(routes[path]())
            except Exception as e: return self.respond({'error':str(e)},400)
    httpd=ThreadingHTTPServer(('127.0.0.1',port),Handler)
    httpd.daemon_threads=True
    return httpd,token
