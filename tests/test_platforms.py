import unittest
from personaweave.platforms import OneBot
class PlatformsTests(unittest.TestCase):
 def test_nonlocal_endpoint_rejected(self):
  with self.assertRaises(ValueError):OneBot('ws://example.com','',lambda *a:None)
 def test_offline_send_fails(self):
  with self.assertRaises(RuntimeError):OneBot('ws://127.0.0.1:3001','',lambda *a:None).send('12345','message')
