"""Optional Windows tray host. Closing the window can keep the host alive."""
import os
import sys
import threading
from pathlib import Path

def autostart(enabled):
    if os.name!='nt': raise RuntimeError('开机自启仅支持 Windows')
    import winreg
    exe=Path(sys.executable).resolve()
    import subprocess
    command=subprocess.list2cmdline([str(exe),'-m','personaweave']) if not getattr(sys,'frozen',False) else subprocess.list2cmdline([str(exe)])
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER,r'Software\Microsoft\Windows\CurrentVersion\Run') as key:
        if enabled: winreg.SetValueEx(key,'PersonaWeave',0,winreg.REG_SZ,command)
        else:
            try: winreg.DeleteValue(key,'PersonaWeave')
            except FileNotFoundError: pass

def launch(url,host):
    import webview
    import pystray
    from PIL import Image,ImageDraw
    window=webview.create_window('织灵 · PersonaWeave',url,width=1220,height=820,min_size=(900,620))
    image=Image.new('RGBA',(64,64),(0,0,0,0));d=ImageDraw.Draw(image)
    d.rounded_rectangle((3,3,61,61),radius=18,fill='#64745b')
    d.line([(17,40),(26,20),(38,44),(47,24)],fill='white',width=4)
    exiting=threading.Event()
    def quit_app(icon,item):
        exiting.set();icon.stop();window.destroy()
    def closing():
        if not exiting.is_set(): window.hide();return False
    def show(icon,item): window.show()
    window.events.closing+=closing
    icon=pystray.Icon('PersonaWeave',image,'织灵',pystray.Menu(pystray.MenuItem('打开织灵',show,default=True),pystray.MenuItem('退出并停止服务',quit_app)))
    thread=threading.Thread(target=icon.run,daemon=True);thread.start()
    try: webview.start(gui='edgechromium' if os.name=='nt' else None)
    finally: icon.stop()
