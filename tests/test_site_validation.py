import importlib.util
from pathlib import Path
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/check_site.py'


class SiteValidationTests(unittest.TestCase):
    def run_check(self, pages, files=()):
        self.assertTrue(SCRIPT.exists(), 'site validator has not been implemented')
        spec = importlib.util.spec_from_file_location('check_site', SCRIPT)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            for name, text in pages.items():
                p = root / name
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(text)
            for name in files:
                p = root / name
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(b'fixture')
            return mod.check_site(root)

    def test_valid_parent_and_encoded_pdf(self):
        errors = self.run_check({
            'docs/index.md': '---\ntitle: Algebra\nhas_children: true\n---\n',
            'docs/note.md': '---\ntitle: Note\nparent: Algebra\nlayout: pdf\npdf: /assets/pdfs/A%20B.pdf\n---\n',
        }, ['assets/pdfs/A B.pdf'])
        self.assertEqual(errors, [])

    def test_missing_parent_and_pdf_are_reported(self):
        errors = self.run_check({'docs/note.md': '---\ntitle: Note\nparent: Missing\nlayout: pdf\npdf: /assets/pdfs/lost.pdf\n---\n'})
        self.assertTrue(any('parent' in e for e in errors), errors)
        self.assertTrue(any('lost.pdf' in e for e in errors), errors)

    def test_filename_control_character_is_reported(self):
        errors = self.run_check({'docs/\x08note.md': '---\ntitle: Note\n---\n'})
        self.assertTrue(any('control' in e for e in errors), errors)

    def test_wrong_pdf_case_is_reported_even_on_macos(self):
        errors = self.run_check({'docs/note.md': '---\ntitle: Note\nlayout: pdf\npdf: /assets/pdfs/note.pdf\n---\n'}, ['assets/pdfs/Note.pdf'])
        self.assertTrue(any('note.pdf' in e for e in errors), errors)

    def test_comment_links_are_ignored_but_active_links_checked(self):
        errors = self.run_check({'docs/note.md': '---\ntitle: Note\n---\n<!-- [old](/missing.pdf) -->\n[open](/real.pdf)'}, ['real.pdf'])
        self.assertEqual(errors, [])

    def test_pdf_layout_requires_pdf_or_explicit_pending_status(self):
        errors = self.run_check({'docs/note.md': '---\ntitle: Note\nlayout: pdf\n---\n'})
        self.assertTrue(any('pdf' in e for e in errors), errors)

    def test_navigation_cycle_is_rejected(self):
        errors = self.run_check({
            'docs/a.md': '---\ntitle: A\nparent: B\nhas_children: true\n---\n',
            'docs/b.md': '---\ntitle: B\nparent: A\nhas_children: true\n---\n',
        })
        self.assertTrue(any('cycle' in e for e in errors), errors)

    def test_related_link_is_checked(self):
        errors = self.run_check({'docs/note.md': '---\ntitle: Note\nrelated:\n  - title: Missing\n    url: /docs/missing.html\n---\n'})
        self.assertTrue(any('missing.html' in e for e in errors), errors)
