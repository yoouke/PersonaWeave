"""Runtime installers, process ownership and native DSH package operations."""
import json, os, re, shutil, subprocess, threading, time, uuid
from pathlib import Path

class RuntimeServices:
    def command(self):
        entry=self.store.root/'runtime'/'dsh'/'node_modules'/'@deepseek-ai'/'dsh'/'dist'/'bin.js'
        # npm package exposes its exact bin in package.json; do not assume dist layout.
        package=entry.parents[1]/'package.json'
        if package.exists():
            meta=json.loads(package.read_text(encoding='utf-8')); bins=meta.get('bin',{})
            rel=bins if isinstance(bins,str) else bins.get('dsh')
            if rel: return [self.node(),str(package.parent/rel)]
        executable=shutil.which('dsh')
        if executable: return [executable]
        raise RuntimeError('DSH 未安装，请在设置中执行安装')

    def node(self):
        local=self.store.root/'runtime'/'node'/'node.exe'
        value=str(local) if local.exists() else shutil.which('node')
        if not value: raise RuntimeError('未找到 Node.js，请先安装 Node.js 24 LTS')
        return value

    def runtime_path(self):
        return os.pathsep.join([str(Path(self.node()).parent),str(self.store.root/'runtime'/'tools'/'node_modules'/'.bin'),os.environ.get('PATH','')])

    def install_dsh(self):
        node=self.node(); npm=Path(node).parent/'node_modules'/'npm'/'bin'/'npm-cli.js'
        target=self.store.root/'runtime'/'dsh'; target.mkdir(parents=True,exist_ok=True)
        cmd=[node,str(npm)] if npm.exists() else [shutil.which('npm') or 'npm']
        p=subprocess.run(cmd+['install','--prefix',str(target),'--save-exact','--ignore-scripts','@deepseek-ai/dsh@0.2.1-rc.5'],capture_output=True,text=True,timeout=600)
        if p.returncode: raise RuntimeError('DSH 安装失败，请检查网络和 Node/npm 环境；依赖构建需在可信环境手动批准')
        tools=self.store.root/'runtime'/'tools'
        tools.mkdir(parents=True,exist_ok=True)
        p=subprocess.run(cmd+['install','--prefix',str(tools),'--save-exact','--ignore-scripts','pnpm@10'],capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=300)
        if p.returncode: raise RuntimeError('DSH 已安装，但插件包管理器 pnpm 安装失败；请重试')
        return {'ok':True,'message':'DSH 0.2.1-rc.5 及 pnpm 已安装，确切版本记录于 package-lock.json'}

    def diagnostics(self):
        result={'node':False,'dsh':False,'qq':bool(self.channel and self.channel.online)}
        try: result['node']=subprocess.run([self.node(),'--version'],capture_output=True,text=True,timeout=10).stdout.strip()
        except Exception as e: result['node_error']=str(e)
        try: result['dsh']=subprocess.run(self.command()+['--version'],capture_output=True,text=True,timeout=20).stdout.strip()
        except Exception as e: result['dsh_error']=str(e)
        return result

    def start_protocol(self):
        c=self.config()
        if c['protocol']!='napcat': raise ValueError('SnowLuma 请使用其官方程序启动；宿主只连接')
        with self.lock:
            previous=self.services.get('napcat')
            if previous and previous.poll() is None: return {'ok':True,'message':'NapCat 已在运行'}
            base=self.store.root/'runtime'/'napcat'
            entry=base/'index.js'; node=base/'node.exe'
            if not entry.exists() or not node.exists(): raise ValueError('未找到 NapCat Node 自包含入口，请安装或检查目录结构')
            logdir=self.store.root/'logs';logdir.mkdir(exist_ok=True)
            with open(logdir/'napcat.log','ab') as log:
                self.services['napcat']=subprocess.Popen([str(node),str(entry)],cwd=base,stdout=log,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,creationflags=0x08000000 if os.name=='nt' else 0)
        return {'ok':True,'message':'NapCat 已启动；登录请使用其官方控制台'}

    def stop_protocol(self):
        if self.channel:self.channel.close()
        p=self.services.pop('napcat',None)
        if p and p.poll() is None:
            if os.name=='nt': subprocess.run(['taskkill','/PID',str(p.pid),'/T','/F'],capture_output=True)
            else:p.terminate()
            p.wait(10)
        return {'ok':True}

    def plugins(self,cid,action,package):
        self.store.character(cid)
        if action not in ('add','remove','update'): raise ValueError('插件操作无效')
        if not re.fullmatch(r'(?:@[a-z0-9_.-]+/)?[a-z0-9_.-]+(?:@[a-zA-Z0-9.^~*-]+)?',package): raise ValueError('请输入 npm 包名，禁止 URL 或命令参数')
        if cid in self.busy: raise ValueError('先停止角色再变更插件')
        env={**os.environ,'DSH_HOME':str(self.store.root/'Characters'/cid/'config'/'dsh'),'PATH':self.runtime_path()}
        p=subprocess.run(self.command()+['plugin','--profile','sdk',action,package],env=env,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=300)
        if p.returncode: raise RuntimeError('插件操作失败，请检查依赖及 DSH 兼容性；'+self.redact((p.stderr or p.stdout or '')[-1800:]))
        return {'ok':True,'message':'包操作完成；插件挂载与启用须按插件文档配置，不会自动猜测工具配置。'}


def extract_result(events):
    answer=''; finish=None
    for event in events:
        # Durable session envelopes use type/data; parse only explicit assistant messages.
        typ=event.get('type'); data=event.get('data',{})
        if typ=='assistant/message':
            blocks=data.get('message',{}).get('content',[]) if isinstance(data,dict) else []
            if isinstance(blocks,str): answer=blocks
            elif isinstance(blocks,list): answer=''.join(b.get('text','') for b in blocks if b.get('type')=='text') or answer
        if typ=='turn/end':
            r=data.get('reason',{})
            finish=r.get('kind') if isinstance(r,dict) else r
    return answer,finish
