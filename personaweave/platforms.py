import asyncio
import json
import threading
import time
from urllib.parse import urlsplit

class OneBot:
    """OneBot v11 forward WebSocket; NapCat and compatible external endpoints."""
    def __init__(self, url, token, receive):
        if urlsplit(url).hostname not in ('127.0.0.1','localhost','::1'):
            raise ValueError('协议端必须连接本机地址')
        self.url,self.token,self.receive=url,token,receive
        self.stop=threading.Event(); self.online=False; self.loop=None; self.ws=None
        self.seen={}
    def start(self): threading.Thread(target=lambda:asyncio.run(self.run()),daemon=True).start()
    async def run(self):
        from websockets.asyncio.client import connect
        self.loop=asyncio.get_running_loop()
        while not self.stop.is_set():
            try:
                async with connect(self.url, additional_headers={'Authorization':'Bearer '+self.token}, max_size=2**20,open_timeout=10) as ws:
                    self.ws=ws; self.online=True
                    async for raw in ws:
                        event=json.loads(raw)
                        if event.get('post_type')!='message' or event.get('message_type')!='private': continue
                        mid=str(event.get('message_id')); now=time.monotonic()
                        self.seen={k:v for k,v in self.seen.items() if now-v<600}
                        if mid in self.seen: continue
                        self.seen[mid]=now
                        segments=event.get('message',[])
                        text=''.join(s.get('data',{}).get('text','') for s in segments if s.get('type')=='text') if isinstance(segments,list) else str(segments)
                        threading.Thread(target=self.receive,args=(str(event['user_id']),text),daemon=True).start()
            except Exception: self.online=False
            if not self.stop.is_set(): await asyncio.sleep(3)
        self.online=False
    def send(self, uid, text):
        if not self.online: raise RuntimeError('QQ 通道尚未连接')
        for offset in range(0,len(text),1800):
            payload={'action':'send_private_msg','params':{'user_id':int(uid),'message':[{'type':'text','data':{'text':text[offset:offset+1800]}}]}}
            asyncio.run_coroutine_threadsafe(self.ws.send(json.dumps(payload)),self.loop).result(15)
    def close(self):
        self.stop.set()
        if self.ws and self.loop: asyncio.run_coroutine_threadsafe(self.ws.close(),self.loop)
