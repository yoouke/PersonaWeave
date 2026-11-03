"""DSH SDK JSON-RPC transport. No GUI or private web endpoints required."""
import json
import os
import queue
import subprocess
import threading
import uuid

class DshEngine:
    def __init__(self, argv, cwd, env, on_event, on_approval):
        self.pending, self.lock, self.writer = {}, threading.Lock(), threading.Lock()
        self.on_event, self.on_approval = on_event, on_approval
        self.proc = subprocess.Popen(argv, cwd=cwd, env={**os.environ, **env}, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8', bufsize=1, creationflags=0x08000000 if os.name=='nt' else 0)
        self.reader=threading.Thread(target=self._read, daemon=True);self.reader.start()
        self.errors=threading.Thread(target=self._stderr, daemon=True);self.errors.start()
    def _send(self, payload):
        with self.writer:
            self.proc.stdin.write(json.dumps(payload, ensure_ascii=False)+'\n'); self.proc.stdin.flush()
    def _stderr(self):
        for line in self.proc.stderr:
            # Diagnostics can contain credentials; do not persist raw stderr.
            self.on_event('diagnostic', {'message':'DSH 发出诊断信息；请在本机 DSH 控制台检查配置。'})
    def _read(self):
        try:
            for line in self.proc.stdout:
                try: msg=json.loads(line)
                except ValueError: continue
                if 'method' in msg:
                    if 'id' in msg:
                        if msg['method']=='approval/request': self.on_approval(msg['id'], msg.get('params', {}), self)
                        else: self._send({'jsonrpc':'2.0','id':msg['id'],'error':{'code':-32601,'message':'Unsupported host request'}})
                    else: self.on_event(msg['method'], msg.get('params', {}))
                else:
                    with self.lock: q=self.pending.get(msg.get('id'))
                    if q: q.put(msg)
        finally:
            with self.lock:
                for q in self.pending.values(): q.put({'error':{'message':'DSH 进程已退出'}})
    def call(self, method, params=None, timeout=120):
        rid=str(uuid.uuid4()); q=queue.Queue()
        with self.lock: self.pending[rid]=q
        try:
            self._send({'jsonrpc':'2.0','id':rid,'method':method,'params':params or {}})
            msg=q.get(timeout=timeout)
            if 'error' in msg: raise RuntimeError(str(msg['error'].get('message','DSH RPC error')))
            return msg.get('result', {})
        finally:
            with self.lock: self.pending.pop(rid,None)
    def approve(self, rid, allowed):
        self._send({'jsonrpc':'2.0','id':rid,'result':{'outcome':'allowed-once' if allowed else 'rejected'}})
    def close(self):
        if self.proc.poll() is None:
            if os.name=='nt': subprocess.run(['taskkill','/PID',str(self.proc.pid),'/T','/F'],capture_output=True)
            else: self.proc.terminate()
            try: self.proc.wait(10)
            except subprocess.TimeoutExpired: self.proc.kill(); self.proc.wait()
        for thread in (self.reader,self.errors):
            if thread is not threading.current_thread(): thread.join(3)
        for stream in (self.proc.stdin,self.proc.stdout,self.proc.stderr):
            if stream and not stream.closed: stream.close()
