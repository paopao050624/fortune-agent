import json
from pathlib import Path
import re
import unittest
from fortune_agent import __version__


class ReleaseMetadataTests(unittest.TestCase):
    def test_release_identifiers_and_current_readme_agree(self):
        root=Path(__file__).resolve().parents[1]
        version=re.search(r'^version = "([^"]+)"',(root/'pyproject.toml').read_text(),re.M)[1]
        self.assertEqual(__version__,version)
        self.assertEqual(json.loads((root/'package.json').read_text())['version'],version)
        self.assertIn(f'**[v{version}]',(root/'README.md').read_text())
        self.assertTrue((root/'docs'/f'release-v{".".join(version.split(".")[:2])}.md').exists())
        self.assertNotIn('docs/release-v0.2.md',(root/'.github/workflows/release.yml').read_text())

    def test_browser_version_check_reads_metadata_and_workflow_runs_each_check_once(self):
        root=Path(__file__).resolve().parents[1]
        script=(root/'scripts/verify_export_retrieval.cjs').read_text()
        self.assertNotIn("includes('v0.3.0')",script)
        self.assertIn('package.json',script)
        commands=[line.strip() for line in (root/'.github/workflows/tests.yml').read_text().splitlines() if line.strip().startswith('node scripts/verify_')]
        self.assertEqual(len(commands),len(set(commands)))
