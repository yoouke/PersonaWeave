"""Verified downloads with bounded extraction. No administrator rights required."""
import hashlib
import json
import os
import shutil
import stat
import tempfile
import urllib.request
import zipfile
from pathlib import Path

def download(url,path,max_bytes=1024**3):
    if not url.startswith('https://'): raise ValueError('Downloads require HTTPS')
    request=urllib.request.Request(url,headers={'User-Agent':'PersonaWeave/0.1'})
    size=0
    with urllib.request.urlopen(request,timeout=60) as response,open(path,'wb') as out:
        while chunk:=response.read(1024*1024):
            size+=len(chunk)
            if size>max_bytes: raise ValueError('下载文件过大')
            out.write(chunk)

def extract(archive,target):
    target=Path(target).resolve()
    with zipfile.ZipFile(archive) as z:
        if sum(x.file_size for x in z.infolist())>4*1024**3: raise ValueError('解压内容过大')
        for info in z.infolist():
            dest=(target/info.filename.replace('\\','/')).resolve()
            if not dest.is_relative_to(target) or stat.S_ISLNK(info.external_attr>>16): raise ValueError('不安全的压缩路径')
        z.extractall(target)

def install_node(root):
    if os.name!='nt': raise RuntimeError('自动安装运行时仅支持 Windows x64')
    import platform
    if platform.machine().lower() not in ('amd64','x86_64'): raise RuntimeError('此安装器暂支持 x64')
    with urllib.request.urlopen('https://nodejs.org/dist/index.json',timeout=30) as r: versions=json.load(r)
    release=next(v for v in versions if v['version'].startswith('v24.') and v.get('lts'))
    version=release['version']; name=f'node-{version}-win-x64.zip'; base='https://nodejs.org/dist/'+version+'/'
    target=Path(root)/'runtime'/'node'
    if target.exists(): raise ValueError('Node 运行时已存在；请先检查版本')
    with tempfile.TemporaryDirectory() as temp:
        temp=Path(temp); archive=temp/name
        download(base+name,archive)
        with urllib.request.urlopen(base+'SHASUMS256.txt',timeout=30) as r: checks=r.read().decode()
        expected=next(line.split()[0] for line in checks.splitlines() if line.split()[-1]==name)
        if hashlib.sha256(archive.read_bytes()).hexdigest()!=expected: raise ValueError('Node 校验失败')
        extract(archive,temp/'out');target.parent.mkdir(parents=True,exist_ok=True)
        shutil.move(str(temp/'out'/f'node-{version}-win-x64'),target)
    return {'ok':True,'version':version}

def install_napcat(root,selected):
    if selected!='napcat': raise ValueError('当前选择 SnowLuma，不安装 NapCat')
    if os.name!='nt': raise RuntimeError('NapCat 自动安装仅支持 Windows')
    target=Path(root)/'runtime'/'napcat'
    if target.exists(): raise ValueError('NapCat 已存在，不覆盖已有登录和配置')
    req=urllib.request.Request('https://api.github.com/repos/NapNeko/NapCatQQ/releases/latest',headers={'User-Agent':'PersonaWeave'})
    with urllib.request.urlopen(req,timeout=30) as r: release=json.load(r)
    asset=next(a for a in release['assets'] if a['name']=='NapCat.Shell.Windows.Node.zip')
    expected=asset.get('digest','')
    if not expected.startswith('sha256:'): raise ValueError('上游未提供 SHA256，停止自动安装')
    with tempfile.TemporaryDirectory() as tmp:
        archive=Path(tmp)/'napcat.zip';download(asset['browser_download_url'],archive)
        if hashlib.sha256(archive.read_bytes()).hexdigest()!=expected.split(':')[1]: raise ValueError('NapCat 校验失败')
        extract(archive,Path(tmp)/'out');target.parent.mkdir(parents=True,exist_ok=True)
        shutil.move(str(Path(tmp)/'out'),target)
    return {'ok':True,'version':release['tag_name'],'message':'已校验并安装。首次登录与 OneBot 正向 WebSocket 配置请使用 NapCat 官方控制台。'}

def configure_napcat(root, bot_qq, url, token):
    """Configure the verified upstream OneBot schema; retain unrelated settings."""
    import re
    from urllib.parse import urlsplit
    from .store import atomic_text
    if not re.fullmatch(r'\d{5,12}', str(bot_qq)):
        raise ValueError('请填写作为机器人使用的 QQ 账号')
    parsed = urlsplit(url)
    if parsed.hostname != '127.0.0.1' or parsed.scheme != 'ws' or parsed.path not in ('', '/') or not parsed.port:
        raise ValueError('自动配置使用 ws://127.0.0.1:端口，不包含路径')
    if not token:
        raise ValueError('请先保存 OneBot Token')
    root = Path(root)/'runtime'/'napcat'
    if not root.exists():
        raise ValueError('请先安装 NapCat')
    config_dir = root/'napcat'/'config' if (root/'napcat').is_dir() else root/'config'
    config_dir.mkdir(parents=True, exist_ok=True)
    path = config_dir/f'onebot11_{bot_qq}.json'
    old = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
    network = old.setdefault('network', {})
    servers = network.setdefault('websocketServers', [])
    servers[:] = [s for s in servers if s.get('name') != 'PersonaWeave']
    servers.append({'name': 'PersonaWeave', 'enable': True, 'host': '127.0.0.1', 'port': parsed.port,
                    'messagePostFormat': 'array', 'reportSelfMessage': False, 'token': token,
                    'enableForcePushEvent': True, 'debug': False, 'heartInterval': 30000})
    if path.exists():
        backup = path.with_suffix('.json.backup')
        if not backup.exists():
            shutil.copy2(path, backup)
    atomic_text(path, json.dumps(old, ensure_ascii=False, indent=2))
    if os.name != 'nt':
        path.chmod(0o600)
    return {'ok': True, 'message': '已按上游格式写入 OneBot 配置；请重启 NapCat 后重新联动。协议端配置按上游要求包含连接 Token。'}
