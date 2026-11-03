import tempfile
import unittest
import zipfile
from pathlib import Path
from personaweave.installers import extract
class InstallerTests(unittest.TestCase):
 def test_zip_escape_rejected(self):
  with tempfile.TemporaryDirectory() as tmp:
   z=Path(tmp)/'bad.zip'
   with zipfile.ZipFile(z,'w') as out:out.writestr('../escape','oops')
   with self.assertRaises(ValueError):extract(z,Path(tmp)/'out')
   self.assertFalse((Path(tmp)/'escape').exists())
