"""Versioned host data; retrieval always carries character and audience scope."""
import base64
import io
import json
import re
import sqlite3
import threading
import uuid
import zipfile
from pathlib import Path


def atomic_text(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(text, encoding='utf-8')
    temp.replace(path)


class Store:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        self.db = sqlite3.connect(self.root / 'host.sqlite', check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.executescript('''
        PRAGMA journal_mode=WAL;
        PRAGMA busy_timeout=10000;
        CREATE TABLE IF NOT EXISTS config(key TEXT PRIMARY KEY, value TEXT);
        CREATE TABLE IF NOT EXISTS characters(id TEXT PRIMARY KEY, data TEXT);
        CREATE TABLE IF NOT EXISTS memory(id TEXT PRIMARY KEY, character_id TEXT, audience TEXT, content TEXT, created TEXT DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY, character_id TEXT, kind TEXT, data TEXT, created TEXT DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS sessions(route TEXT PRIMARY KEY, session_id TEXT, persisted INTEGER DEFAULT 0);
        CREATE TABLE IF NOT EXISTS knowledge(id TEXT PRIMARY KEY, character_id TEXT, audience TEXT, title TEXT, content TEXT, created TEXT DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS conversations(id INTEGER PRIMARY KEY, character_id TEXT, audience TEXT, user TEXT, assistant TEXT, created TEXT DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS usage(id TEXT PRIMARY KEY, character_id TEXT, model TEXT, purpose TEXT, input_tokens INTEGER, output_tokens INTEGER, estimated INTEGER, cost REAL, currency TEXT, created TEXT DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS tasks(id TEXT PRIMARY KEY, data TEXT);
        CREATE TABLE IF NOT EXISTS plugins(id TEXT PRIMARY KEY, data TEXT);
        ''')
        columns = {r[1] for r in self.db.execute('PRAGMA table_info(memory)')}
        for name, definition in [('kind', "TEXT DEFAULT 'event'"), ('automatic', 'INTEGER DEFAULT 0')]:
            if name not in columns:
                self.db.execute(f'ALTER TABLE memory ADD COLUMN {name} {definition}')
        self.db.commit()
        self.set('schema_version', 2)
        for task in self.saved_tasks():
            if task['state'] in ('running', 'queued'):
                task.update(state='interrupted', error='程序已重启；任务未自动重放，请检查结果后重试。')
                self.save_task(task)

    def rows(self, sql, args=()):
        with self.lock:
            return [dict(r) for r in self.db.execute(sql, args).fetchall()]

    def write(self, sql, args=()):
        with self.lock:
            self.db.execute(sql, args)
            self.db.commit()

    def get(self, key, default=None):
        rows = self.rows('SELECT value FROM config WHERE key=?', (key,))
        return json.loads(rows[0]['value']) if rows else default

    def set(self, key, value):
        self.write('INSERT OR REPLACE INTO config VALUES (?,?)', (key, json.dumps(value)))

    def character(self, cid):
        if not isinstance(cid, str) or not re.fullmatch(r'[a-f0-9-]{36}', cid):
            raise ValueError('角色 ID 无效')
        rows = self.rows('SELECT data FROM characters WHERE id=?', (cid,))
        if not rows:
            raise ValueError('角色不存在')
        return json.loads(rows[0]['data'])

    def characters(self):
        return [json.loads(r['data']) for r in self.rows('SELECT data FROM characters')]

    def save_character(self, data):
        with self.lock:
            previous = self.character(data['id']) if data.get('id') else {}
            cid = previous.get('id') or str(uuid.uuid4())
            name = str(data.get('name', previous.get('name', ''))).strip()[:120]
            if not name:
                raise ValueError('请填写角色名')
            clean = {**previous, 'id': cid, 'name': name}
            defaults = dict(personality='', plugins=[], avatar='', portrait='', voice={}, sources=[], engine='dsh', auto_memory=False, behavior='')
            for key, default in defaults.items():
                clean[key] = data.get(key, previous.get(key, default))
            if clean['engine'] not in ('dsh', 'openai'):
                raise ValueError('未知引擎')
            if not isinstance(clean['plugins'], list) or not isinstance(clean['sources'], list):
                raise ValueError('插件和来源必须为列表')
            for key in ('avatar', 'portrait'):
                image = clean[key]
                if image and (not isinstance(image, str) or not re.fullmatch(r'data:image/(?:png|jpeg|webp);base64,[A-Za-z0-9+/=]+', image) or len(image) > 3_000_000):
                    raise ValueError('头像/立绘仅支持 2MB 内的 PNG/JPEG/WebP')
            base = self.root / 'Characters' / cid
            for folder in ('memory', 'knowledge', 'assets', 'config', 'logs', 'workspace'):
                (base / folder).mkdir(parents=True, exist_ok=True)
            atomic_text(base / 'character.json', json.dumps(clean, ensure_ascii=False, indent=2))
            atomic_text(base / 'personality.md', clean['personality'])
            self.write('INSERT OR REPLACE INTO characters VALUES (?,?)', (cid, json.dumps(clean)))
            return clean

    def event(self, cid, kind, data):
        self.write('INSERT INTO events(character_id,kind,data) VALUES (?,?,?)', (cid, kind, json.dumps(data, ensure_ascii=False)))

    @staticmethod
    def rank(rows, query, limit=1000):
        if not query.strip():
            return rows[:limit]
        terms = re.findall(r'[\w]+', query.lower())
        terms += [query[i:i+2].lower() for i in range(len(query)-1) if '\u4e00' <= query[i] <= '\u9fff']
        terms = list(dict.fromkeys(terms))[:80]
        scored = [(sum((r.get('title', '')+' '+r['content']).lower().count(t) for t in terms), r) for r in rows]
        return [r for score, r in sorted(scored, key=lambda pair: pair[0], reverse=True) if score > 0][:limit]

    def memories(self, cid, audience, query=''):
        self.character(cid)
        rows = self.rows('SELECT * FROM memory WHERE character_id=? AND audience IN (?,?) ORDER BY created DESC,rowid DESC LIMIT 1000', (cid, audience, 'public'))
        return self.rank(rows, query)

    def add_memory(self, cid, audience, text, kind='event', automatic=False):
        self.character(cid)
        text = str(text).strip()
        if not text or len(text) > 20000 or kind not in ('event', 'relationship', 'fact', 'experience'):
            raise ValueError('记忆内容或类型无效（最长 20000 字符）')
        mid = str(uuid.uuid4())
        with self.lock:
            existing = self.rows('SELECT id FROM memory WHERE character_id=? AND audience=? AND content=?', (cid, audience, text))
            if existing:
                return existing[0]['id']
            self.write('INSERT INTO memory(id,character_id,audience,content,kind,automatic) VALUES (?,?,?,?,?,?)', (mid, cid, audience, text, kind, int(automatic)))
        return mid

    def edit_memory(self, cid, mid, text, audience, kind='event'):
        self.character(cid)
        if not text.strip() or kind not in ('event', 'relationship', 'fact', 'experience'):
            raise ValueError('记忆内容或类型无效')
        self.write('UPDATE memory SET content=?,audience=?,kind=? WHERE id=? AND character_id=?', (text[:20000], audience, kind, mid, cid))
        return {'ok': True}

    def knowledge(self, cid, audience, query=''):
        self.character(cid)
        rows = self.rows('SELECT * FROM knowledge WHERE character_id=? AND audience IN (?,?) ORDER BY created DESC LIMIT 500', (cid, audience, 'public'))
        return self.rank(rows, query)

    def add_knowledge(self, cid, audience, title, content):
        self.character(cid)
        if not content.strip() or len(content) > 500000:
            raise ValueError('知识文档为空或超过 50 万字符')
        kid = str(uuid.uuid4())
        self.write('INSERT INTO knowledge(id,character_id,audience,title,content) VALUES (?,?,?,?,?)', (kid, cid, audience, title[:200], content))
        atomic_text(self.root/'Characters'/cid/'knowledge'/(kid+'.md'), content)
        return {'id': kid}

    def history(self, cid, audience, limit=20):
        self.character(cid)
        return list(reversed(self.rows('SELECT * FROM conversations WHERE character_id=? AND audience=? ORDER BY id DESC LIMIT ?', (cid, audience, min(100, limit)))))

    def save_task(self, task):
        self.write('INSERT OR REPLACE INTO tasks VALUES (?,?)', (task['id'], json.dumps(task, ensure_ascii=False)))

    def saved_tasks(self):
        return [json.loads(r['data']) for r in self.rows('SELECT data FROM tasks ORDER BY rowid DESC LIMIT 200')][::-1]

    def export_character(self, cid, include_private=False):
        char = {k: v for k, v in self.character(cid).items() if k not in ('id', 'plugins')}
        result = {'format': 'personaweave-character', 'version': 1, 'character': char}
        if include_private:
            result['memory'] = self.rows('SELECT audience,content,kind FROM memory WHERE character_id=?', (cid,))
            result['knowledge'] = self.rows('SELECT audience,title,content FROM knowledge WHERE character_id=?', (cid,))
        output = io.BytesIO()
        with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as archive:
            archive.writestr('character.json', json.dumps(result, ensure_ascii=False, indent=2))
            archive.writestr('personality.md', char['personality'])
        return output.getvalue()

    def import_character(self, payload):
        raw = base64.b64decode(payload, validate=True)
        if len(raw) > 8_000_000:
            raise ValueError('角色包过大')
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            info = archive.getinfo('character.json')
            if info.file_size > 12_000_000:
                raise ValueError('角色包解压后过大')
            data = json.loads(archive.read(info))
        if data.get('format') != 'personaweave-character' or data.get('version') != 1:
            raise ValueError('不支持的角色包格式')
        char = self.save_character({**data['character'], 'id': None, 'plugins': [], 'auto_memory': False})
        for item in data.get('memory', [])[:1000]:
            self.add_memory(char['id'], 'imported-private', item['content'], item.get('kind', 'event'))
        for item in data.get('knowledge', [])[:100]:
            self.add_knowledge(char['id'], 'imported-private', item['title'], item['content'])
        return char

    def backup(self):
        target = self.root / 'backups'
        target.mkdir(exist_ok=True)
        path = target / ('host-' + str(uuid.uuid4()) + '.sqlite')
        with self.lock, sqlite3.connect(path) as destination:
            self.db.backup(destination)
        return {'ok': True, 'file': str(path), 'message': '私密数据库备份已保存在本机；凭据库不在备份内。'}


class Vault:
    def __init__(self, namespace):
        self.namespace = 'PersonaWeave:' + str(namespace)
        self.known = set()

    def get(self, name):
        import keyring
        value = keyring.get_password(self.namespace, name) or ''
        if value: self.known.add(value)
        return value

    def set(self, name, value):
        import keyring
        keyring.set_password(self.namespace, name, value)
        if value: self.known.add(value)
