"""Explicit release tests, no discovery, external services or user records."""
import ast
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
class Release(unittest.TestCase):
    def test_version(self):
        tag=re.search(r'^## (v[^\s]+)$',(ROOT/'CHANGELOG.md').read_text(),re.M)[1]
        self.assertEqual(tag,'v0.3.0-alpha.2')
        for name,pattern in [('app/web/product.html',r'<title>PTDS - ([^<]+)</title>'),
                             ('app/web/ptds_live.js',r"id = 'sidebar-version'; version.textContent = '([^']+)'")]:
            self.assertEqual(re.findall(pattern,(ROOT/name).read_text()),[tag[1:]])
        self.assertIn('## '+tag,(ROOT/'CHANGELOG.en.md').read_text())
    def test_sources_and_example(self):
        for f in (ROOT/'app').rglob('*.py'):ast.parse(f.read_bytes(),str(f.relative_to(ROOT)))
        cfg=json.loads((ROOT/'config.example.json').read_bytes())
        self.assertFalse(cfg['band_bridge']);self.assertFalse(cfg['starling']['enabled'])
        self.assertNotIn('oura',cfg)
        self.assertEqual(set(cfg['device_targets'].values()),{cfg['instances'][0]['key']})
        sample=(ROOT/'data/sample-import.csv').read_text().splitlines()
        self.assertEqual(len(sample),3);self.assertEqual(sample[1],sample[2])
    def test_package_tools(self):
        for tool in ['scripts/verify_release.py','scripts/check_publication.py']:
            with tempfile.TemporaryDirectory() as tmp:
                p=subprocess.run([sys.executable,'-B','-I',str(ROOT/tool)],env={'PATH':'/usr/bin:/bin','HOME':tmp,'TMPDIR':tmp},capture_output=True,text=True,timeout=45)
                self.assertEqual(p.returncode,0,p.stdout+p.stderr)
if __name__=='__main__':unittest.main(verbosity=2)
