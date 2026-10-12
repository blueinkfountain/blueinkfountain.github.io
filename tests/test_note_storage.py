import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue((ROOT / 'scripts/note_storage.py').exists(), 'storage implementation is missing')
        import note_storage
        self.storage = note_storage
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root / 'snapshot'
        self.source.mkdir()
        self.published = self.root / 'untexed-current'
        self.published.mkdir()
        self.output = self.root / '_data/records.yml'
        self.output.parent.mkdir()
        self.output.write_text('old: true\n')
        (self.published / 'kept.pdf').write_bytes(b'unchanged')
        (self.published / 'deleted.pdf').write_bytes(b'old')
        (self.source / 'kept.pdf').write_bytes(b'unchanged')
        (self.source / 'new.pdf').write_bytes(b'new')

    def test_cache_reuses_exact_value_and_invalidates_content_and_settings(self):
        pdf = self.source / 'new.pdf'
        cache = self.storage.MetricCache(self.root / 'cache', {'scale': 2})
        self.assertEqual(cache.get('total', pdf, lambda: 1234567), 1234567)
        def fail(): raise AssertionError('unchanged PDF was recomputed')
        self.assertEqual(cache.get('total', pdf, fail), 1234567)
        pdf.write_bytes(b'changed')
        self.assertEqual(cache.get('total', pdf, lambda: 12), 12)
        cache = self.storage.MetricCache(self.root / 'cache', {'scale': 3})
        self.assertEqual(cache.get('total', pdf, lambda: 99), 99)

    def test_corrupt_cache_is_recomputed(self):
        cache = self.storage.MetricCache(self.root / 'cache', {'scale': 2})
        pdf = self.source / 'new.pdf'
        cache.get('total', pdf, lambda: 40)
        for p in (self.root / 'cache').glob('*.json'): p.write_text('{')
        self.assertEqual(cache.get('total', pdf, lambda: 41), 41)

    def test_publication_reuses_unchanged_pdf_and_updates_pair(self):
        inode = (self.published / 'kept.pdf').stat().st_ino
        result = self.storage.publish_snapshot(self.source, self.published, self.output, {'new': True})
        self.assertEqual((self.published / 'kept.pdf').stat().st_ino, inode)
        self.assertEqual((self.published / 'new.pdf').read_bytes(), b'new')
        self.assertFalse((self.published / 'deleted.pdf').exists())
        self.assertEqual(yaml.safe_load(self.output.read_text()), {'new': True})
        self.assertEqual(result, {'reused': 1, 'copied': 1})

    def test_copy_failure_keeps_old_pair(self):
        with patch.object(self.storage.shutil, 'copy2', side_effect=OSError('disk full')):
            with self.assertRaises(OSError):
                self.storage.publish_snapshot(self.source, self.published, self.output, {'new': True})
        self.assertEqual(self.output.read_text(), 'old: true\n')
        self.assertEqual((self.published / 'deleted.pdf').read_bytes(), b'old')

    def test_yaml_swap_failure_rolls_back_pdfs(self):
        real_replace = self.storage.os.replace
        def replace(src, dst):
            if Path(src).name == 'next.yml': raise OSError('cannot publish YAML')
            return real_replace(src, dst)
        with patch.object(self.storage.os, 'replace', side_effect=replace):
            with self.assertRaises(OSError):
                self.storage.publish_snapshot(self.source, self.published, self.output, {'new': True})
        self.assertEqual(self.output.read_text(), 'old: true\n')
        self.assertTrue((self.published / 'deleted.pdf').exists())
        self.assertFalse((self.published / 'new.pdf').exists())

    def test_interrupted_swap_recovers_on_next_run(self):
        real_replace = self.storage.os.replace
        def replace(src, dst):
            if Path(src).name == 'next.yml': raise KeyboardInterrupt()
            return real_replace(src, dst)
        with patch.object(self.storage.os, 'replace', side_effect=replace):
            with self.assertRaises(KeyboardInterrupt):
                self.storage.publish_snapshot(self.source, self.published, self.output, {'new': True})
        self.storage.recover_publication(self.published, self.output)
        self.assertEqual(self.output.read_text(), 'old: true\n')
        self.assertTrue((self.published / 'deleted.pdf').exists())

    def test_empty_snapshot_is_rejected(self):
        for p in self.source.iterdir(): p.unlink()
        with self.assertRaises(ValueError):
            self.storage.publish_snapshot(self.source, self.published, self.output, {})
        self.assertTrue((self.published / 'deleted.pdf').exists())
