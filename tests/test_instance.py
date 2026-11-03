import tempfile
import unittest
from personaweave.instance import InstanceLock
class InstanceTests(unittest.TestCase):
 def test_exclusive_and_released(self):
  with tempfile.TemporaryDirectory() as root:
   first=InstanceLock(root)
   try:
    with self.assertRaises(RuntimeError):InstanceLock(root)
   finally:first.close()
   second=InstanceLock(root);second.close()
