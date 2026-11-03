import json
import tempfile
import threading
import unittest
import urllib.request
import urllib.error
from personaweave.host import Host
from personaweave.server import server
class HttpTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.host=Host(self.tmp.name);self.s,self.token=server(self.host)
  threading.Thread(target=self.s.serve_forever,daemon=True).start();self.base='http://127.0.0.1:'+str(self.s.server_port)
 def tearDown(self):self.s.shutdown();self.s.server_close();self.host.store.db.close();self.tmp.cleanup()
 def test_auth_required(self):
  with self.assertRaises(urllib.error.HTTPError) as e:urllib.request.urlopen(self.base+'/api/config')
  self.assertEqual(e.exception.code,403)
 def test_character_roundtrip(self):
  req=urllib.request.Request(self.base+'/api/character',data=json.dumps({'name':'Test','personality':'<script>untrusted</script>'}).encode(),headers={'X-Token':self.token,'Content-Type':'application/json'})
  with urllib.request.urlopen(req) as r: self.assertEqual(json.load(r)['name'],'Test')
  req=urllib.request.Request(self.base+'/api/characters',headers={'X-Token':self.token})
  with urllib.request.urlopen(req) as r:self.assertEqual(len(json.load(r)),1)
 def test_origin_rejected(self):
  req=urllib.request.Request(self.base+'/api/config',headers={'X-Token':self.token,'Origin':'https://evil.example'})
  with self.assertRaises(urllib.error.HTTPError) as e:urllib.request.urlopen(req)
  self.assertEqual(e.exception.code,403)
