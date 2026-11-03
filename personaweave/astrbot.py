"""Manage upstream AstrBot plugins through the API used by DSQQ.

No QQ receiver, memory engine, image generator or DSH bridge is implemented here.
"""
import copy
import hashlib
import json
import time
from urllib.parse import quote, urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, build_opener
from .vendor.astrbot_api import Api
from .agent_context import persona_text


# The six identifiers below come from DSQQ's MIT config pack, not npm search.
PRESETS = [
    ('astrbot_plugin_group_chat_plus', '群聊表达', 'Him666233/astrbot_plugin_group_chat_plus'),
    ('astrbot_plugin_livingmemory', '长期记忆', 'lxfight/astrbot_plugin_livingmemory'),
    ('meme_manager', '表情包管理', 'anka/meme_manager'),
    ('astrbot_plugin_qzone', 'QQ 空间', 'Zhalslar/astrbot_plugin_qzone'),
    ('astrbot_plugin_qqprofile', 'QQ 资料', 'Zhalslar/astrbot_plugin_qqprofile'),
    ('astrbot_plugin_proactive_chat', '主动聊天', 'DBJD-CR/astrbot_plugin_proactive_chat'),
    ('astrbot_plugin_dsh', 'DSH 桥接', 'CCYellowStar2/astrbot_plugin_dsh'),
]


def local_url(value):
    parsed = urlsplit(str(value))
    if (parsed.scheme not in ('http', 'https') or parsed.hostname not in ('127.0.0.1', '::1')
            or parsed.username or parsed.password or parsed.query or parsed.fragment
            or parsed.path not in ('', '/') or not parsed.port):
        raise ValueError('请输入本机 AstrBot 地址，例如 http://127.0.0.1:6185')
    return f'{parsed.scheme}://{parsed.netloc}'


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise ValueError('AstrBot 接口重定向已拒绝，请检查本机地址')


class LocalApi(Api):
    def __init__(self, url):
        super().__init__(local_url(url))
        self.opener = build_opener(ProxyHandler({}), NoRedirect())

    def call(self, method, path, body=None, timeout=10, **kwargs):
        return super().call(method, path, body, timeout=timeout, **kwargs)


class AstrBotPlugins:
    def __init__(self, host):
        self.host, self.store = host, host.store

    def bindings(self):
        return self.store.get('astrbot_bindings', {})

    def bind(self, data):
        cid = data['character_id']
        self.store.character(cid)
        process = self.host.services.get('napcat')
        if process and process.poll() is None and self.host.config()['character_id'] == cid:
            raise ValueError('请先停止织灵管理的 NapCat，再连接已有 DSQQ，避免同时运行两个协议端')
        url = local_url(data['url'])
        bindings = self.bindings()
        if any(k != cid and v['url'] == url for k, v in bindings.items()):
            raise ValueError('此 AstrBot 实例已绑定其他角色；请为每个角色使用独立实例和数据目录')
        user = str(data.get('username', '')).strip()
        if not user:
            raise ValueError('请填写 AstrBot 后台账号')
        password = str(data.get('password') or self.host.vault.get('astrbot:'+cid))
        if not password:
            raise ValueError('请填写 AstrBot 后台密码')
        api = LocalApi(url)
        if not api.login(user, password):
            raise ValueError('AstrBot 登录失败，请检查后台账号、密码及二步验证要求')
        # Require the real plugin API before recording a binding.
        self.checked(api.call('GET', '/plugins'))
        self.host.vault.set('astrbot:'+cid, password)
        if bindings.get(cid, {}).get('url') != url:
            self.store.set('astrbot_sync:'+cid, {})
        bindings[cid] = {'url': url, 'username': user}
        self.store.set('astrbot_bindings', bindings)
        if cid == self.host.config()['character_id'] and self.host.channel:
            self.host.channel.close()
            self.host.channel = None
            self.host.channels.pop('qq', None)
        return {'ok': True, 'message': '已连接 AstrBot 插件管理接口；QQ 登录状态请查看原生控制台。'}

    def api(self, cid):
        self.store.character(cid)
        binding = self.bindings().get(cid)
        if not binding:
            raise ValueError('请先连接该角色的 DSQQ / AstrBot 实例')
        api = LocalApi(binding['url'])
        if not api.login(binding['username'], self.host.vault.get('astrbot:'+cid)):
            raise ValueError('AstrBot 登录失效，请重新连接')
        return api

    def unbind(self, cid):
        self.store.character(cid)
        bindings = self.bindings()
        bindings.pop(cid, None)
        self.store.set('astrbot_bindings', bindings)
        self.host.vault.set('astrbot:'+cid, '')
        self.store.set('astrbot_sync:'+cid, {})
        return {'ok': True, 'message': '已移除管理连接；原生 AstrBot 服务和插件数据继续由原程序管理。'}

    @staticmethod
    def checked(result):
        if not Api.ok(result):
            # Do not expose upstream exception text, which may contain API keys.
            raise RuntimeError('AstrBot 拒绝操作或插件加载失败，请在其原生控制台查看详情')
        return result.get('data')

    def catalog(self, cid=''):
        installed = {}
        if cid and cid in self.bindings():
            rows = self.checked(self.api(cid).call('GET', '/plugins'))
            if not isinstance(rows, list):
                raise ValueError('AstrBot 插件列表格式不兼容，预期 4.29.3 API')
            installed = {p.get('name'): p for p in rows if isinstance(p, dict)}
        return {'binding': self.bindings().get(cid), 'sync': self.sync_status(cid) if cid else {}, 'plugins': [
            {'id': name, 'name': title, 'repository': 'https://github.com/'+repo,
             'source': 'DSQQ 配置包' if name != 'astrbot_plugin_dsh' else '现有 AstrBot→DSH 桥',
             'installed': name in installed, 'version': installed.get(name, {}).get('version', ''),
             'enabled': installed.get(name, {}).get('activated', installed.get(name, {}).get('enabled'))}
            for name, title, repo in PRESETS]}

    def operate(self, cid, plugin_id, action):
        with self.host.lock:
            if cid in self.host.busy or cid in self.host.maintenance:
                raise ValueError('角色正在运行或维护，请稍后重试')
            self.host.maintenance.add(cid)
        try:
            return self._operate(cid, plugin_id, action)
        finally:
            with self.host.lock:
                self.host.maintenance.discard(cid)

    def _operate(self, cid, plugin_id, action):
        preset = next((p for p in PRESETS if p[0] == plugin_id), None)
        if not preset:
            raise ValueError('请从 DSQQ 同款插件清单选择插件')
        api, pid = self.api(cid), quote(plugin_id, safe='')
        if action == 'install':
            present = self.checked(api.call('GET', '/plugins'))
            if any(p.get('name') == plugin_id for p in present if isinstance(p, dict)):
                return {'ok': True, 'message': '已安装，保留现有配置和数据。'}
            body = ({'install_method': 'repository', 'repository': 'https://github.com/'+preset[2]}
                    if plugin_id == 'astrbot_plugin_dsh' else
                    {'install_method': 'market', 'market_plugin_id': preset[2]})
            self.checked(api.call('POST', '/plugins/install/github', body, timeout=600))
            # Keep new capabilities disabled until configured in the native UI.
            self.checked(api.call('PATCH', f'/plugins/{pid}/enabled', {'enabled': False}))
            present = self.checked(api.call('GET', '/plugins'))
            if not any(p.get('name') == plugin_id for p in present if isinstance(p, dict)):
                raise RuntimeError('AstrBot 未返回安装记录，不能标记为安装成功')
        elif action in ('enable', 'disable'):
            if plugin_id == 'astrbot_plugin_dsh' and action == 'enable':
                raise ValueError('请先使用「配置主人专用 DSH 桥」完成权限检查')
            if action == 'enable':
                self.owner_instance(api)
            self.checked(api.call('PATCH', f'/plugins/{pid}/enabled', {'enabled': action == 'enable'}))
        elif action in ('update', 'reload'):
            if plugin_id == 'astrbot_plugin_dsh':
                raise ValueError('DSH 桥请先在原生控制台停用后更新，再重新检查主人权限')
            self.checked(api.call('POST', f'/plugins/{pid}/{action}', {}, timeout=600))
        elif action == 'remove':
            self.checked(api.call('DELETE', '/plugins/by-id?plugin_id='+pid, {}))
        else:
            raise ValueError('未知插件操作')
        return {'ok': True, 'message': '操作已由 AstrBot 执行；详细配置请打开原生插件控制台。'}

    def bridge(self, cid, ingress_url, token):
        owner = str(self.host.config()['owner'])
        if not owner:
            raise ValueError('请先在通信平台中绑定主人 QQ')
        if not token:
            process = self.host.services.get('dsh-web')
            if not process or process.poll() is not None or getattr(self.host, 'native_web_cid', None) != cid:
                raise ValueError('请先启动此角色的原生 DSH 控制台，或填写外部 ingress token')
            path = self.store.root/'Characters'/cid/'config'/'dsh'/'astrbot-ingress.json'
            try:
                beacon = json.loads(path.read_text(encoding='utf-8'))
            except (OSError, ValueError):
                raise ValueError('DSH ingress 尚未就绪，请确认已安装插件并稍后重试')
            if beacon.get('kind') != 'dsh-astrbot-ingress' or beacon.get('pid') != process.pid or not beacon.get('token'):
                raise ValueError('DSH ingress 信标与当前角色进程不匹配')
            ingress_url, token = beacon['url'], beacon['token']
        ingress_url = local_url(ingress_url)
        getattr(self.host.vault, 'known', set()).add(token)
        api = self.api(cid)
        self.owner_instance(api)
        conf = self.checked(api.call('GET', '/plugins/config?plugin_id=astrbot_plugin_dsh')).get('config')
        if not isinstance(conf, dict):
            raise ValueError('请先安装 DSH 桥接插件')
        conf = copy.deepcopy(conf)
        conf.update(enabled=True, ingress_url=ingress_url, token=token, allow_users=[owner],
                    allow_groups=[], private_passthrough=False, session_scope='user', command='dsh')
        self.checked(api.call('PUT', '/plugins/config', {'plugin_id': 'astrbot_plugin_dsh', 'config': conf}))
        self.checked(api.call('POST', '/plugins/astrbot_plugin_dsh/reload', {}))
        self.checked(api.call('PATCH', '/plugins/astrbot_plugin_dsh/enabled', {'enabled': True}))
        return {'ok': True, 'message': '已配置现有桥接插件：只有主人私聊可发送 /dsh 任务。'}

    def sync_persona(self, cid):
        with self.host.lock:
            if cid in self.host.busy or cid in self.host.maintenance:
                raise ValueError('角色正在运行或维护，请稍后同步')
            self.host.maintenance.add(cid)
        try:
            return self._sync_persona(cid)
        except Exception:
            state = self.store.get('astrbot_sync:'+cid, {})
            self.store.set('astrbot_sync:'+cid, {**state, 'error': '人格同步失败，本地设定已保留；请检查实例连接和主人白名单后重试。'})
            raise
        finally:
            with self.host.lock:
                self.host.maintenance.discard(cid)

    @staticmethod
    def persona_digest(char):
        return hashlib.sha256(persona_text(char, 'astrbot').encode()).hexdigest()

    def sync_status(self, cid):
        char = self.store.character(cid)
        state = self.store.get('astrbot_sync:'+cid, {})
        return {'automatic': state.get('automatic', False),
                'pending': state.get('digest') != self.persona_digest(char),
                'last_success': state.get('last_success'), 'error': state.get('error', '')}

    def sync_policy(self, cid, enabled):
        self.store.character(cid)
        if cid not in self.bindings():
            raise ValueError('请先连接该角色的 AstrBot 实例')
        if not isinstance(enabled, bool):
            raise ValueError('自动同步设置必须为布尔值')
        with self.host.lock:
            state = self.store.get('astrbot_sync:'+cid, {})
            self.store.set('astrbot_sync:'+cid, {**state, 'automatic': enabled})
        return {'ok': True, 'message': '已开启自动同步：保存角色及重新联动时同步。' if enabled else '已关闭自动同步。'}

    def sync_if_needed(self, cid):
        state = self.sync_status(cid)
        if state['automatic'] and state['pending']:
            try:
                return self.sync_persona(cid)
            except Exception:
                return {'ok': False, 'message': '本地角色已保存，AstrBot 同步未完成；请检查连接、主人白名单后重试。'}
        return {'ok': True, 'message': '设定已同步。' if not state['pending'] else '未开启自动同步，请手动同步当前设定。'}

    def _sync_persona(self, cid):
        char = self.store.character(cid)
        api = self.api(cid)
        cfg = copy.deepcopy(self.owner_instance(api))
        persona_id = 'personaweave-'+cid
        path = '/personas/'+quote(persona_id, safe='')
        current = api.call('GET', path)
        if not Api.ok(current) and current.get('_http') != 404:
            self.checked(current)
        body = {'system_prompt': persona_text(char, 'astrbot'), 'tools': None}
        exists = Api.ok(current) and isinstance(current.get('data'), dict) and current['data'].get('persona_id') == persona_id
        if exists:
            self.checked(api.call('PUT', path, body))
        else:
            self.checked(api.call('POST', '/personas', {**body, 'persona_id': persona_id, 'begin_dialogs': []}))
        cfg.setdefault('agent_runner', {}).setdefault('config', {}).setdefault('persona', {})['persona_id'] = persona_id
        self.checked(api.call('PUT', '/config-profiles/default', {'config': cfg}))
        state = self.store.get('astrbot_sync:'+cid, {})
        self.store.set('astrbot_sync:'+cid, {**state, 'digest': self.persona_digest(char),
                                           'last_success': time.time(), 'error': ''})
        return {'ok': True, 'message': '已将当前角色设定同步到此 AstrBot 实例；插件记忆继续由原生插件管理。'}

    def readiness(self, cid):
        """Read-only checks; never claim QQ login or model execution from API health."""
        self.store.character(cid)
        checks = []
        if cid not in self.bindings():
            return {'checks': [{'name': 'AstrBot', 'state': 'error', 'message': '尚未连接此角色的独立实例。'}]}
        try:
            api = self.api(cid)
            rows = self.checked(api.call('GET', '/plugins'))
            if not isinstance(rows, list):
                raise ValueError('插件列表格式不兼容')
            checks.append({'name': 'AstrBot', 'state': 'ok', 'message': '后台认证与插件接口可用。'})
        except Exception:
            return {'checks': [{'name': 'AstrBot', 'state': 'error', 'message': '无法连接或后台认证失效，请检查地址、服务和账号。'}]}
        try:
            self.owner_instance(api)
            checks.append({'name': '主人权限', 'state': 'ok', 'message': '仅主人私聊白名单检查通过。'})
        except Exception:
            checks.append({'name': '主人权限', 'state': 'error', 'message': '请绑定主人，并在原生控制台设为唯一管理员和私聊白名单。'})
        sync = self.sync_status(cid)
        checks.append({'name': '人格设定', 'state': 'warning' if sync['pending'] else 'ok',
                       'message': '本地设定尚未同步，请点击同步。' if sync['pending'] else '本地设定与上次成功同步版本一致。'})
        bridge = next((r for r in rows if isinstance(r, dict) and r.get('name') == 'astrbot_plugin_dsh'), {})
        active = bridge.get('activated', bridge.get('enabled', False))
        checks.append({'name': 'DSH 桥接插件', 'state': 'ok' if active else 'warning',
                       'message': 'AstrBot 返回桥接已启用；不代表消息往返已验证。' if active else '桥接未安装或未启用，请安装并配置主人专用桥。'})
        process = self.host.services.get('dsh-web')
        live = bool(process and process.poll() is None and getattr(self.host, 'native_web_cid', None) == cid)
        checks.append({'name': '本角色 DSH 控制台', 'state': 'ok' if live else 'warning',
                       'message': '本角色进程正在运行。' if live else '本角色进程未运行；如使用外部 DSH，请在其控制台检查。'})
        checks.append({'name': 'QQ 登录与真实消息', 'state': 'unknown',
                       'message': '请在 AstrBot / NapCat 控制台检查；后台接口正常不能证明 QQ 已登录。'})
        return {'checks': checks, 'sync': sync}

    def prepare(self, cid):
        """Idempotent preparation via existing installers; do not enable unconfigured tools."""
        self.owner_instance(self.api(cid))
        steps = []
        operations = [('长期记忆插件', lambda: self.operate(cid, 'astrbot_plugin_livingmemory', 'install')),
                      ('AstrBot 桥接插件', lambda: self.operate(cid, 'astrbot_plugin_dsh', 'install')),
                      ('DSH ingress 插件', lambda: self.host.install_native('ingress', cid)),
                      ('人格设定', lambda: self.sync_persona(cid))]
        for name, operation in operations:
            try:
                operation()
                steps.append({'name': name, 'state': 'ok'})
            except Exception:
                steps.append({'name': name, 'state': 'error'})
                return {'ok': False, 'steps': steps, 'message': name+'准备失败；已完成的安装保留，可修复后重试。'}
        return {'ok': True, 'steps': steps, 'message': '基础组件和人格已准备；请在原生控制台配置记忆服务、模型，再启动 DSH 并配置主人专用桥。插件不会提前启用。'}

    def owner_instance(self, api):
        owner = str(self.host.config()['owner'])
        if not owner:
            raise ValueError('请先绑定主人 QQ')
        cfg = self.checked(api.call('GET', '/config-profiles/default')).get('config', {})
        ps = cfg.get('platform_settings', {})
        platforms = [p for p in cfg.get('platform', []) if p.get('enable') and p.get('type') == 'aiocqhttp']
        # Upstream plugins can run tools: enforce the owner-only instance boundary.
        if set(map(str, cfg.get('admins_id', []))) != {owner} or not ps.get('enable_id_white_list'):
            raise ValueError('该 AstrBot 实例必须仅有主人一位管理员，并开启消息白名单；请在原生控制台设置')
        sessions = {owner} | {str(p['id'])+':FriendMessage:'+owner for p in platforms}
        whitelist = set(map(str, ps.get('id_whitelist', [])))
        if not whitelist or not whitelist <= sessions:
            raise ValueError('AstrBot 白名单仅可包含主人的私聊，群聊或其他身份不能开放主人工具')
        return cfg
