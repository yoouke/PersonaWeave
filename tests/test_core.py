import json
import sys
import tempfile
import unittest
from pathlib import Path
from personaweave.store import Store
from personaweave.engine import DshEngine
from personaweave.host import extract_result, Host

class CoreTests(unittest.TestCase):
 def setUp(self): self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup); self.s=Store(self.tmp.name); self.addCleanup(self.s.db.close)
 def test_character_and_memory_isolation(self):
  a=self.s.save_character({'name':'A','personality':'原始设定'});b=self.s.save_character({'name':'B'})
  self.s.add_memory(a['id'],'owner','秘密');self.s.add_memory(a['id'],'public','公开');self.s.add_memory(b['id'],'owner','其他角色')
  self.assertEqual(len(self.s.memories(a['id'],'owner')),2);self.assertEqual([x['content'] for x in self.s.memories(a['id'],'stranger')],['公开'])
  self.assertEqual((Path(self.tmp.name)/'Characters'/a['id']/'personality.md').read_text(encoding='utf-8'),'原始设定')
 def test_invalid_path(self):
  with self.assertRaises(ValueError): self.s.character('../../escape')
 def test_failed_turn_not_success(self):
  self.assertEqual(extract_result([{'type':'turn/end','data':{'reason':{'kind':'error'}}}])[1],'error')
 def test_rpc_interleaved_approval(self):
  script=Path(self.tmp.name)/'fake.py';script.write_text('''import json,sys
for line in sys.stdin:
 m=json.loads(line)
 if m.get('method')=='initialize':
  print(json.dumps({'jsonrpc':'2.0','id':99,'method':'approval/request','params':{'toolName':'shell'}}),flush=True)
 elif m.get('id')==99:
  print(json.dumps({'jsonrpc':'2.0','id':first,'result':{'ok':True}}),flush=True)
 if m.get('method')=='initialize': first=m['id']
''')
  approvals=[]
  def approval(rid,p,e): approvals.append(p);e.approve(rid,False)
  engine=DshEngine([sys.executable,str(script)],self.tmp.name,{},lambda *a:None,approval)
  self.addCleanup(engine.close)
  self.assertTrue(engine.call('initialize',{},5)['ok']);self.assertEqual(approvals[0]['toolName'],'shell')
 def test_unknown_qq_sender_cannot_submit(self):
  h=Host(Path(self.tmp.name)/'host');self.addCleanup(h.store.db.close)
  h.store.set('settings',{'owner':'12345'})
  h.receive('99999','执行任务');self.assertFalse(h.tasks)

if __name__=='__main__':unittest.main()

class ResultContractTests(unittest.TestCase):
 def test_actual_dsh_message_envelope(self):
  events=[{'type':'assistant/message','data':{'message':{'content':[{'type':'text','text':'你好'}]}}},{'type':'turn/end','data':{'reason':{'kind':'completed'}}}]
  self.assertEqual(extract_result(events),('你好','completed'))
