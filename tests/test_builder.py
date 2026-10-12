from contextlib import redirect_stdout
import importlib.util
import io
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import fitz
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))


class BuilderTests(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.spec_from_file_location('builder_under_test', ROOT / 'scripts/build_untexed_records.py')
        self.builder = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.builder)
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        b = self.builder
        b.ROOT = root
        b.SNAPSHOT_ROOT = root / 'untexed'
        b.PUBLISHED_ROOT = root / 'untexed-current'
        b.OUTPUT = root / '_data/records.yml'
        b.GRID_TEMPLATE_PDF = root / 'blank.pdf'
        b.INK_REFERENCE_PDF = root / 'reference.pdf'
        self.make_pdf(b.GRID_TEMPLATE_PDF, blank=True)
        self.make_pdf(b.INK_REFERENCE_PDF)
        self.make_pdf(b.SNAPSHOT_ROOT / '261001/Algebra/note.pdf')
        with redirect_stdout(io.StringIO()): b.initialize_ink_calibration()

    def make_pdf(self, path, blank=False):
        path.parent.mkdir(parents=True, exist_ok=True)
        doc = fitz.open()
        page = doc.new_page(width=100, height=100)
        if not blank: page.draw_rect(fitz.Rect(20, 20, 60, 60), color=(0,0,0), fill=(0,0,0))
        doc.save(path)
        doc.close()

    def test_cached_total_avoids_rendering_but_preserves_exact_pixels(self):
        b = self.builder
        pdf = b.SNAPSHOT_ROOT / '261001/Algebra/note.pdf'
        total = b.count_total_ink_pixels(pdf)
        self.assertGreater(total, 0)
        with patch.object(b, 'page_ink_mask', side_effect=AssertionError('PDF rendered twice')):
            self.assertEqual(b.count_total_ink_pixels(pdf), total)

    def test_cached_visual_hash_avoids_pdf_open(self):
        b = self.builder
        pdf = b.SNAPSHOT_ROOT / '261001/Algebra/note.pdf'
        visual = b.visual_pdf_hash(pdf)
        with patch.object(b.fitz, 'open', side_effect=AssertionError('PDF reopened')):
            self.assertEqual(b.visual_pdf_hash(pdf), visual)

    def test_builder_preserves_frozen_record_and_latest_urls(self):
        b = self.builder
        for date in ['261002','261003','261004']:
            self.make_pdf(b.SNAPSHOT_ROOT / date / 'Algebra/note.pdf')
        with redirect_stdout(io.StringIO()): b.main()
        first = yaml.safe_load(b.OUTPUT.read_text())
        first['records']['261001']['note'] = 'frozen note'
        b.OUTPUT.write_text(yaml.safe_dump(first))
        self.make_pdf(b.SNAPSHOT_ROOT / '261005/Algebra/note.pdf')
        with redirect_stdout(io.StringIO()): b.main()
        after = yaml.safe_load(b.OUTPUT.read_text())
        self.assertEqual(after['records']['261001'], first['records']['261001'])
        self.assertEqual(after['latest_date'], '261005')
        self.assertEqual(after['records']['261005']['library_total_ink_percent'], 100.0)
        self.assertTrue((b.PUBLISHED_ROOT / 'Algebra/note.pdf').exists())
