import json
import sqlite3
import threading
import uuid
from pathlib import Path

class Store:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        self.db = sqlite3.connect(self.root / 'host.sqlite', check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.executescript('''
        PRAGMA journal_mode=WAL;
        CREATE TABLE IF NOT EXISTS config(key TEXT PRIMARY KEY, value TEXT);
        CREATE TABLE IF NOT EXISTS characters(id TEXT PRIMARY KEY, data TEXT);
        CREATE TABLE IF NOT EXISTS memory(id TEXT PRIMARY KEY, character_id TEXT, audience TEXT, content TEXT, created TEXT DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY, character_id TEXT, kind TEXT, data TEXT, created TEXT DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS sessions(route TEXT PRIMARY KEY, session_id TEXT, persisted INTEGER DEFAULT 0);
        ''')
        self.db.commit()
    def rows(self, sql, args=()):
        with self.lock:
            return [dict(r) for r in self.db.execute(sql, args).fetchall()]
    def write(self, sql, args=()):
        with self.lock:
            self.db.execute(sql, args)
            self.db.commit()
    def get(self, key, default=None):
        r = self.rows('SELECT value FROM config WHERE key=?', (key,))
        return json.loads(r[0]['value']) if r else default
    def set(self, key, value):
        self.write('INSERT OR REPLACE INTO config VALUES (?,?)', (key, json.dumps(value)))
    def character(self, cid):
        if not cid or not all(c in '0123456789abcdef-' for c in cid):
            raise ValueError('角色 ID 无效')
        rows = self.rows('SELECT data FROM characters WHERE id=?', (cid,))
        if not rows: raise ValueError('角色不存在')
        return json.loads(rows[0]['data'])
    def characters(self):
        return [json.loads(r['data']) for r in self.rows('SELECT data FROM characters')]
    def save_character(self, data):
        cid = data.get('id') or str(uuid.uuid4())
        if data.get('id'): self.character(cid)
        name = str(data.get('name', '')).strip()
        if not name: raise ValueError('请填写角色名')
        base = self.root / 'Characters' / cid
        for folder in ('memory', 'knowledge', 'assets', 'config', 'logs', 'workspace'):
            (base / folder).mkdir(parents=True, exist_ok=True)
        clean = {'id': cid, 'name': name, 'personality': str(data.get('personality', '')), 'plugins': data.get('plugins', []), 'avatar': str(data.get('avatar', ''))}
        for filename, text in [('character.json', json.dumps(clean, ensure_ascii=False, indent=2)), ('personality.md', clean['personality'])]:
            tmp = base / (filename + '.tmp')
            tmp.write_text(text, encoding='utf-8'); tmp.replace(base / filename)
        self.write('INSERT OR REPLACE INTO characters VALUES (?,?)', (cid, json.dumps(clean)))
        return clean
    def event(self, cid, kind, data):
        self.write('INSERT INTO events(character_id,kind,data) VALUES (?,?,?)', (cid, kind, json.dumps(data, ensure_ascii=False)))
    def memories(self, cid, audience):
        self.character(cid)
        return self.rows('SELECT * FROM memory WHERE character_id=? AND audience IN (?,?) ORDER BY created DESC', (cid, audience, 'public'))
    def add_memory(self, cid, audience, text):
        self.character(cid)
        mid = str(uuid.uuid4())
        self.write('INSERT INTO memory(id,character_id,audience,content) VALUES (?,?,?,?)', (mid,cid,audience,text))
        return mid

class Vault:
    """OS credential backend only; never silently falls back to plaintext."""
    def __init__(self, namespace): self.namespace = 'PersonaWeave:' + str(namespace)
    def get(self, name):
        import keyring
        return keyring.get_password(self.namespace, name) or ''
    def set(self, name, value):
        import keyring
        keyring.set_password(self.namespace, name, value)
