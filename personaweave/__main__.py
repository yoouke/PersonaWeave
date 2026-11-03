import argparse
import os
import threading
import webbrowser
from pathlib import Path
from .host import Host
from .server import server
from .instance import InstanceLock

def main():
    p=argparse.ArgumentParser(description='织灵 PersonaWeave')
    p.add_argument('--data',default=str(Path(os.environ.get('LOCALAPPDATA',Path.home()/'.local/share'))/'PersonaWeave'))
    p.add_argument('--browser',action='store_true'); p.add_argument('--port',type=int,default=0)
    args=p.parse_args(); lock=InstanceLock(args.data); host=Host(args.data); httpd,token=server(host,args.port)
    url=f'http://127.0.0.1:{httpd.server_port}/#'+token
    threading.Thread(target=httpd.serve_forever,daemon=True).start()
    try:
        if not args.browser:
            try:
                from .desktop import launch
                launch(url,host)
                return
            except ImportError: pass
        webbrowser.open(url)
        print('PersonaWeave 已启动；浏览器窗口中的地址含本机管理凭据，请勿分享。Ctrl+C 退出。')
        threading.Event().wait()
    except KeyboardInterrupt: pass
    finally: host.close(); httpd.shutdown(); httpd.server_close(); lock.close()
if __name__=='__main__': main()
