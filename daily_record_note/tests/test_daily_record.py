import importlib.util
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
import yaml
import json

MODULE = Path(__file__).resolve().parents[1] / "daily_record.py"
spec = importlib.util.spec_from_file_location('daily_record', MODULE)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class RecordStoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name)
        (self.repo / '_data').mkdir()
        (self.repo / 'untexed' / '261007').mkdir(parents=True)
        (self.repo / 'untexed' / '261009').mkdir(parents=True)
        (self.repo / 'untexed' / '261010').mkdir(parents=True)
        self.yaml_path = self.repo / '_data' / 'untexed_records.yml'
        self.yaml_path.write_text(yaml.safe_dump({
            'latest_date': '261009',
            'dates': ['261009', '261007'],
            'records': {
                '261007': {'note': 'Study algebra', 'baseline': False, 'total_ink_percent': 12.3},
                '261009': {'note': 'Study geometry', 'baseline': False, 'file_total_ink_percent': {'A/a.pdf': 40.2}},
            }
        }, sort_keys=False), encoding='utf-8')

    def store(self):
        return module.RecordStore(self.repo)

    def test_latest_new_note_visible_immediately_and_survives_reopening(self):
        store = self.store()
        self.assertEqual(store.note_for('261010'), '')
        store.save_note('261010', 'Read Rudin')
        self.assertEqual(store.note_for('261010'), 'Read Rudin')
        self.assertEqual(self.store().note_for('261010'), 'Read Rudin')
        self.assertEqual(store.pending_for_latest(), 'Read Rudin')
        self.assertEqual(store.context_rows('261010')[-1][1], 'Read Rudin')
        # No premature skeleton record should appear in the YAML.
        raw = yaml.safe_load(self.yaml_path.read_text())
        self.assertNotIn('261010', raw['records'])

    def test_stale_pending_for_old_day_never_applies_to_new_day(self):
        store = self.store()
        store.save_note('261010', 'Carryover?')
        (self.repo / 'untexed' / '261011').mkdir()
        newer = self.store()
        self.assertEqual(newer.latest_local_date, '261011')
        self.assertIsNone(newer.pending_for_latest())
        self.assertEqual(newer.note_for('261010'), 'Carryover?')
        self.assertEqual(newer.note_for('261011'), '')
        newer.clear_applied_pending()
        self.assertTrue(newer.pending_path.exists())

    def test_existing_note_save_is_atomic_and_preserves_other_stats(self):
        store = self.store()
        store.save_note('261009', 'New edit')
        raw = yaml.safe_load(self.yaml_path.read_text())
        self.assertEqual(raw['records']['261009']['note'], 'New edit')
        self.assertEqual(raw['records']['261009']['file_total_ink_percent'], {'A/a.pdf': 40.2})
        self.assertFalse(store.pending_path.exists())
        self.assertTrue(list((self.repo / '.daily_record_backup').glob('*.yml')))

    def test_clear_existing_note_and_latest_pending(self):
        store = self.store()
        store.save_note('261007', '')
        self.assertEqual(self.store().note_for('261007'), '')
        store.save_note('261010', '')
        self.assertEqual(store.pending_for_latest(), '/clear')
        self.assertEqual(self.store().note_for('261010'), '')

    def test_untracked_historical_date_cannot_silently_discard_edit(self):
        store = self.store()
        with self.assertRaisesRegex(ValueError, 'not editable'):
            store.save_note('261008', 'Lost forever')
        self.assertFalse(store.pending_path.exists())

    def test_snapshot_navigation_does_not_show_uneditable_local_folders(self):
        store = self.store()
        self.assertEqual(store.date_keys, ['261007', '261009', '261010'])
        self.assertEqual(store.previous_key('261010'), '261009')
        self.assertEqual(store.next_key('261007'), '261009')

    def test_existing_latest_stored_to_yaml_not_pending_file(self):
        store = self.store()
        store.save_note('261009', 'Historical')
        self.assertFalse(store.pending_path.exists())
        self.assertEqual(store.note_for('261009'), 'Historical')

    def test_unapplied_old_pending_must_not_be_overwritten(self):
        store = self.store()
        store.save_note('261010', 'Unpublished note')
        (self.repo / 'untexed' / '261011').mkdir()
        newer = self.store()
        with self.assertRaisesRegex(ValueError, 'unapplied note'):
            newer.save_note('261011', 'New note')
        data = json.loads(newer.pending_path.read_text())
        self.assertEqual(data, {'date': '261010', 'note': 'Unpublished note'})

    def test_pending_can_be_consumed_only_for_exact_latest_date(self):
        store = self.store()
        store.save_note('261010', 'New note')
        self.assertTrue(store.pending_path.exists())
        self.assertEqual(store.pending_for_latest(), 'New note')
        store.clear_applied_pending()
        self.assertFalse(store.pending_path.exists())

    def test_initial_intro_labels_real_today_and_prior_calendar_day(self):
        store = self.store()
        today = datetime(2026, 10, 11)
        intro = module.make_intro_text(store, today)
        self.assertIn('Today is 2026-10-11', intro)
        self.assertIn('Latest snapshot: 2026-10-10', intro)
        self.assertNotIn('Today is 2026-10-10', intro)
        self.assertNotIn('Yesterday, you did Study geometry', intro)

    def test_literal_clear_text_is_explicitly_reserved(self):
        store = self.store()
        with self.assertRaisesRegex(ValueError, 'reserved'):
            store.save_note('261010', '/clear')

if __name__ == '__main__':
    unittest.main()
