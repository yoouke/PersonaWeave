import os
import traceback
from pathlib import Path
from personaweave.__main__ import main
if __name__ == '__main__':
    try:
        main()
    except Exception:
        folder=Path(os.environ.get('LOCALAPPDATA',Path.home()))/'PersonaWeave'
        folder.mkdir(parents=True,exist_ok=True)
        (folder/'startup-error.log').write_text(traceback.format_exc(),encoding='utf-8')
        if os.name=='nt':
            import ctypes
            ctypes.windll.user32.MessageBoxW(None,'程序启动失败。诊断记录：'+str(folder/'startup-error.log'),'织灵 · PersonaWeave',0x10)
        else:
            raise
