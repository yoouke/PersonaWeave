"""Plugin registry and DSH overlay compiler; external capabilities stay native."""
import json
import re
import uuid
from .models import endpoint, request_json
from urllib.parse import quote
from .store import atomic_text

PACKAGE = re.compile(r'(?:@[a-z0-9_.-]+/)?[a-z0-9_.-]+(?:@[a-zA-Z0-9.^~*-]+)?')
RESERVED = {'system-prompt', 'credentials', 'authorization', 'deepseek-account'}


class Extensions:
    def __init__(self, host):
        self.host = host
        self.store = host.store

    def catalog(self, query):
        query = str(query).strip()[:150]
        if not query:
            raise ValueError('请输入能力关键词')
        result = request_json('https://registry.npmjs.org/-/v1/search?text='+quote(query+' dsh')+'&size=12')
        return [{'name': x['package']['name'], 'version': x['package']['version'],
                 'description': x['package'].get('description', ''), 'url': x['package'].get('links', {}).get('npm', '')}
                for x in result.get('objects', [])]

    def inspect(self, package):
        if not PACKAGE.fullmatch(package):
            raise ValueError('包名无效')
        name = package.rsplit('@', 1)[0] if '@' in package[1:] else package
        meta = request_json('https://registry.npmjs.org/'+quote(name, safe=''))
        version = package.rsplit('@', 1)[1] if '@' in package[1:] else meta.get('dist-tags', {}).get('latest')
        current = meta.get('versions', {}).get(version)
        if not current:
            raise ValueError('版本不存在，请指定确切版本')
        return {'package': name+'@'+version, 'name': name, 'description': current.get('description', ''),
                'readme': str(meta.get('readme', ''))[:30000], 'license': current.get('license', ''),
                'dependencies': current.get('dependencies', {}), 'engines': current.get('engines', {}),
                'bundle': bool(current.get('dsh', {}).get('bundle'))}

    def list(self):
        return [json.loads(r['data']) for r in self.store.rows('SELECT data FROM plugins')]

    def save(self, data):
        pid = data.get('id') or 'pw-'+uuid.uuid4().hex[:16]
        if not re.fullmatch(r'pw-[a-f0-9]{16}', pid):
            raise ValueError('插件 ID 无效')
        kind = data.get('kind', 'dsh')
        if kind not in ('dsh', 'mcp', 'custom'):
            raise ValueError('插件类型无效')
        package = data.get('package', '')
        if kind in ('dsh', 'custom') and not PACKAGE.fullmatch(package):
            raise ValueError('请输入 npm 包名；自定义插件请先发布或本地安装到 DSH')
        config = data.get('config', {})
        if not isinstance(config, dict):
            raise ValueError('插件配置须为 JSON 对象')
        # Refuse obvious secrets in on-disk JSON. Secret values are supplied separately.
        def inspect(value):
            if isinstance(value, dict):
                for key, item in value.items():
                    if re.search(r'key|password|secret|token|authorization', key, re.I) and isinstance(item, str) and item and '${credential:' not in item:
                        raise ValueError('敏感字段请使用 ${credential:PW_名称} 引用，再在凭据区保存值')
                    inspect(item)
            elif isinstance(value, list):
                for item in value:
                    inspect(item)
        inspect(config)
        if kind == 'mcp':
            if config.get('transport') not in ('stdio', 'streamable-http'):
                raise ValueError('MCP transport 须为 stdio 或 streamable-http')
            if not re.fullmatch(r'[A-Za-z0-9_-]{1,32}', config.get('serverName', '')):
                raise ValueError('MCP serverName 无效')
            if config['transport'] == 'stdio':
                if not config.get('command') or not isinstance(config.get('args', []), list):
                    raise ValueError('stdio 需要 command 和参数数组')
            else:
                endpoint(config.get('url', ''))
            config = {**config, 'expandTemplates': True}
            package = '@deepseek-ai/dsh-mcp-client'
        prior = next((p for p in self.list() if p['id'] == pid), {})
        plugin = {'id': pid, 'name': str(data.get('name', package))[:120], 'kind': kind, 'package': package,
                  'description': str(data.get('description', ''))[:10000], 'documentation': str(data.get('documentation', ''))[:30000], 'instructions': str(data.get('instructions', ''))[:30000],
                  'permissions': data.get('permissions', []), 'config': config, 'schema': data.get('schema', {}),
                  'category': str(data.get('category', 'general'))[:50], 'installed': prior.get('installed', []),
                  'bundles': prior.get('bundles', {}), 'entry_id': str(data.get('entry_id', prior.get('entry_id', '')))[:120]}
        if not isinstance(plugin['permissions'], list) or not isinstance(plugin['schema'], dict):
            raise ValueError('权限须为列表、配置 Schema 须为对象')
        old_name = prior.get('package', '').rsplit('@',1)[0] if '@' in prior.get('package', '')[1:] else prior.get('package', '')
        new_name = package.rsplit('@',1)[0] if '@' in package[1:] else package
        if prior.get('installed') and (old_name != new_name or prior['kind'] != kind):
            raise ValueError('已安装插件不能改为另一个包或类型，请先卸载或新建定义')
        if prior and any(cid in self.host.busy or cid in self.host.maintenance for cid in prior['installed']):
            raise ValueError('请停止相关角色再修改插件配置')
        self.store.write('INSERT OR REPLACE INTO plugins VALUES (?,?)', (pid, json.dumps(plugin, ensure_ascii=False)))
        return plugin

    def operate(self, cid, pid, action):
        with self.host.lock:
            if cid in self.host.busy or cid in self.host.maintenance:
                raise ValueError('角色正在运行或维护')
            self.host.maintenance.add(cid)
        try:
            return self._operate(cid, pid, action)
        finally:
            with self.host.lock:
                self.host.maintenance.discard(cid)

    def _operate(self, cid, pid, action):
        char = self.store.character(cid)
        if cid in self.host.busy:
            raise ValueError('请先停止角色')
        plugin = next((p for p in self.list() if p['id'] == pid), None)
        if not plugin:
            raise ValueError('插件不存在')
        profile_path = self.store.root/'Characters'/cid/'config'/'dsh'/'profiles'/'sdk'/'package.json'
        package_name = plugin['package'].rsplit('@', 1)[0] if '@' in plugin['package'][1:] else plugin['package']
        if action in ('add', 'update', 'remove'):
            other_users = [p for p in self.list() if p['id'] != pid and cid in p['installed'] and (p['package'].rsplit('@',1)[0] if '@' in p['package'][1:] else p['package']) == package_name]
            if action != 'remove' or not other_users:
                target = package_name if action == 'remove' else plugin['package']
                self.host.plugins(cid, action, target)
            if profile_path.exists():
                manifest = json.loads(profile_path.read_text(encoding='utf-8'))
                selected = manifest.get('dsh', {}).get('profile', {}).get('bundles', [])
                plugin.setdefault('bundles', {})[cid] = package_name in selected or plugin.get('bundles', {}).get(cid, False)
                # CLI add auto-selects bundles. Host activation is an independent step.
                if package_name in selected and plugin['id'] not in char['plugins']:
                    manifest['dsh']['profile']['bundles'] = [p for p in selected if p != package_name]
                    atomic_text(profile_path, json.dumps(manifest, ensure_ascii=False, indent=2))
            installed = set(plugin['installed'])
            if action == 'remove':
                installed.discard(cid)
            else:
                installed.add(cid)
            plugin['installed'] = sorted(installed)
            self.store.write('INSERT OR REPLACE INTO plugins VALUES (?,?)', (pid, json.dumps(plugin, ensure_ascii=False)))
        enabled = set(char['plugins'])
        if action == 'enable':
            if cid not in plugin['installed']:
                raise ValueError('请先为该角色安装插件')
            enabled.add(pid)
        elif action in ('disable', 'remove'):
            enabled.discard(pid)
        elif action not in ('add', 'update'):
            raise ValueError('无效插件操作')
        if plugin.get('bundles', {}).get(cid) and action in ('enable', 'disable', 'remove'):
            manifest = json.loads(profile_path.read_text(encoding='utf-8'))
            selection = manifest.setdefault('dsh', {}).setdefault('profile', {}).setdefault('bundles', [])
            selection[:] = [p for p in selection if p != package_name]
            if action == 'enable':
                selection.append(package_name)
            atomic_text(profile_path, json.dumps(manifest, ensure_ascii=False, indent=2))
        self.store.save_character({**char, 'plugins': sorted(enabled)})
        return {'ok': True}

    def patch(self, cid):
        char = self.store.character(cid)
        rows, docs = [], []
        for plugin in self.list():
            enabled = plugin['id'] in char['plugins']
            if not enabled:
                continue  # Registry entries are mounted only here, never auto-loaded.
            if cid not in plugin['installed']:
                raise ValueError('已启用插件缺少安装记录：'+plugin['name'])
            package_name = plugin['package'].rsplit('@', 1)[0] if '@' in plugin['package'][1:] else plugin['package']
            if plugin.get('bundles', {}).get(cid):
                if plugin.get('config'):
                    if not plugin.get('entry_id') or plugin['entry_id'] in RESERVED:
                        raise ValueError('Bundle 配置需要有效的原生条目 ID，且不能覆盖宿主核心条目')
                    rows.append({'id': plugin['entry_id'], 'config': plugin['config'], '_override': True})
            else:
                rows.append({'id': plugin['id'], 'name': package_name, 'config': plugin['config']})
            if plugin['instructions']:
                docs.append(plugin['name']+'：\n'+plugin['instructions'])
        return rows, '\n\n'.join(docs)

    def secret(self, name, value):
        if not re.fullmatch(r'PW_[A-Z0-9_]{1,60}', name):
            raise ValueError('插件凭据名称使用 PW_ 开头的大写字母/数字/下划线')
        self.host.vault.set(name, value)
        names = set(self.store.get('plugin_secret_names', []))
        names.add(name)
        self.store.set('plugin_secret_names', sorted(names))
        return {'ok': True}

    def env(self):
        return {name: self.host.vault.get(name) for name in self.store.get('plugin_secret_names', [])}
