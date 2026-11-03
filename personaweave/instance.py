"""Per-data-directory OS lock, released automatically after a crash."""
from pathlib import Path

class InstanceLock:
    def __init__(self, root):
        root=Path(root);root.mkdir(parents=True,exist_ok=True)
        self.file=open(root/'host.lock','a+b')
        self.file.seek(0,2)
        if self.file.tell()==0:
            self.file.write(b'0');self.file.flush()
        self.file.seek(0)
        try:
            import os
            if os.name=='nt':
                import msvcrt
                msvcrt.locking(self.file.fileno(),msvcrt.LK_NBLCK,1)
            else:
                import fcntl
                fcntl.flock(self.file,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except OSError:
            self.file.close();raise RuntimeError('织灵已在使用此数据目录运行，请从托盘打开现有窗口。')
    def close(self):self.file.close()
