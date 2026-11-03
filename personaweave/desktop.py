"""Optional Windows tray host. Closing the window can keep the host alive."""
import os
import sys
import threading
from pathlib import Path

def autostart(enabled, data=None):
    if os.name!='nt': raise RuntimeError('开机自启仅支持 Windows')
    import winreg
    exe=Path(sys.executable).resolve()
    import subprocess
    args=[str(exe),'-m','personaweave'] if not getattr(sys,'frozen',False) else [str(exe)]
    if data: args += ['--data', str(data)]
    command=subprocess.list2cmdline(args)
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER,r'Software\Microsoft\Windows\CurrentVersion\Run') as key:
        if enabled: winreg.SetValueEx(key,'PersonaWeave',0,winreg.REG_SZ,command)
        else:
            try: winreg.DeleteValue(key,'PersonaWeave')
            except FileNotFoundError: pass

def launch(url,host):
    import webview
    import pystray
    from PIL import Image
    window=webview.create_window('织灵 · PersonaWeave',url,width=1220,height=820,min_size=(900,620))
    with Image.open(Path(__file__).parent/'web'/'icon.png') as source:
        image=source.convert('RGBA').resize((64,64))
    custom=host.config().get('theme',{}).get('icon')
    if custom:
        import base64,io
        try:
            with Image.open(io.BytesIO(base64.b64decode(custom.split(',',1)[1]))) as source:
                if source.width<=1024 and source.height<=1024: image=source.convert('RGBA').resize((64,64))
        except Exception: pass
    exiting=threading.Event()
    def quit_app(icon,item):
        exiting.set();icon.stop();window.destroy()
    def closing():
        if not exiting.is_set() and host.config().get('background',True): window.hide();return False
    def show(icon,item): window.show()
    window.events.closing+=closing
    icon=pystray.Icon('PersonaWeave',image,'织灵',pystray.Menu(pystray.MenuItem('打开织灵',show,default=True),pystray.MenuItem('退出并停止服务',quit_app)))
    thread=threading.Thread(target=icon.run,daemon=True);thread.start()
    try: webview.start(gui='edgechromium' if os.name=='nt' else None)
    finally: icon.stop()
