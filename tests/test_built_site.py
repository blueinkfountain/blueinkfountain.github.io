from pathlib import Path
import importlib.util
import tempfile
import unittest


class BuiltSiteTests(unittest.TestCase):
    def test_generated_handwritten_links_must_have_published_pdfs(self):
        script = Path(__file__).resolve().parents[1] / 'scripts/check_build.py'
        self.assertTrue(script.exists(), 'built-site validator is missing')
        spec = importlib.util.spec_from_file_location('check_build', script)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / 'index.html').write_text('<a href="/untexed-current/A%20B.pdf">note</a>')
            errors = module.check_build(root)
            self.assertTrue(any('A B.pdf' in e for e in errors), errors)
            (root / 'untexed-current').mkdir()
            (root / 'untexed-current/A B.pdf').write_bytes(b'pdf')
            self.assertEqual(module.check_build(root), [])
            (root / 'scripts').mkdir()
            (root / 'scripts/private.py').write_text('private')
            self.assertTrue(any('scripts/private.py' in e for e in module.check_build(root)))
