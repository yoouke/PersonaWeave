import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from personaweave.agent_context import agent_context, export_context, persona_text, WORKSPACE_GUIDE
from personaweave.host import Host


class AgentContextTests(unittest.TestCase):
    def test_guide_describes_software_without_granting_tools_or_replacing_persona(self):
        char = {'personality': 'ORIGINAL-PERSONA', 'behavior': 'ORIGINAL-BEHAVIOR'}
        for mode in ('sdk', 'web', 'chat', 'astrbot'):
            prompt = persona_text(char, mode)
            self.assertIn('织灵（PersonaWeave）', prompt)
            self.assertIn('工具列表是当前能力的依据', prompt)
            self.assertIn('ORIGINAL-PERSONA', prompt)
            self.assertIn('ORIGINAL-BEHAVIOR', prompt)
        self.assertIn('没有电脑操作和插件工具', agent_context('chat'))
        self.assertIn('/dsh', agent_context('astrbot'))
        with self.assertRaises(ValueError):
            agent_context('invented-engine')

    def test_export_is_only_public_guide_and_preserves_existing_workspace_instructions(self):
        with tempfile.TemporaryDirectory() as root:
            workspace = Path(root)
            (workspace/'AGENTS.md').write_text('USER-WORKSPACE-RULES')
            guide = export_context(workspace, 'sdk')
            self.assertEqual(guide.name, WORKSPACE_GUIDE)
            self.assertEqual(guide.read_text(encoding='utf-8'), agent_context('sdk'))
            self.assertEqual((workspace/'AGENTS.md').read_text(), 'USER-WORKSPACE-RULES')
            self.assertNotIn('ORIGINAL-PERSONA', guide.read_text(encoding='utf-8'))

    def test_plain_chat_actually_receives_runtime_context(self):
        with tempfile.TemporaryDirectory() as root:
            host = Host(root)
            char = host.store.save_character({'name': 'test', 'engine': 'openai', 'personality': 'KEEP-MY-PERSONA'})
            host.configure({'model': 'test-model'})
            called = threading.Event()
            messages = []
            def chat(items, *args):
                messages.extend(items)
                called.set()
                return 'OK'
            try:
                with patch.object(host.models, 'chat', side_effect=chat):
                    task = host.submit(char['id'], 'owner', 'Help me with a task.')
                    self.assertTrue(called.wait(3))
                    deadline = time.monotonic()+3
                    while host.busy and time.monotonic() < deadline:
                        time.sleep(.01)
                    self.assertEqual(host.tasks[task['id']]['state'], 'completed')
                self.assertIn('织灵（PersonaWeave）', messages[0]['content'])
                self.assertIn('KEEP-MY-PERSONA', messages[0]['content'])
                self.assertIn('没有电脑操作和插件工具', messages[0]['content'])
                self.assertFalse((Path(root)/'Characters'/char['id']/'workspace'/WORKSPACE_GUIDE).exists())
            finally:
                host.close()
                host.store.db.close()
