# Build on Windows: python -m PyInstaller --noconfirm packaging/windows.spec
from pathlib import Path
from PyInstaller.utils.hooks import collect_all, collect_submodules
root = Path(SPECPATH).parent
web_datas, web_bins, web_hidden = collect_all('webview')
tray_hidden = collect_submodules('pystray')
a = Analysis([str(root / 'entry.py')], pathex=[str(root)],
    binaries=web_bins,
    datas=web_datas + [(str(root/'personaweave'/'web'), 'personaweave/web'),
                       (str(root/'THIRD_PARTY_NOTICES.md'), '.'),
                       (str(root/'personaweave'/'vendor'/'LICENSE'), 'personaweave/vendor')],
    hiddenimports=web_hidden + tray_hidden + ['keyring.backends.Windows', 'win32timezone'],
    hookspath=[], runtime_hooks=[], excludes=['tkinter'], noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='PersonaWeave',
    debug=False, bootloader_ignore_signals=False, strip=False, upx=False,
    console=False, icon=str(root/'packaging'/'icon.ico'))
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='PersonaWeave')
