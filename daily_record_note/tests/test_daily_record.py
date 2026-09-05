import importlib.util
from pathlib import Path
import tempfile
import unittest
import yaml

MODULE_PATH = Path(__file__).resolve().parents[1] / "daily_record.py"
spec = importlib.util.spec_from_file_location("daily_record", MODULE_PATH)
daily_record = importlib.util.module_from_spec(spec)
spec.loader.exec_module(daily_record)


class DailyRecordCoreTests(unittest.TestCase):
    def make_repo(self):
        td = tempfile.TemporaryDirectory()
        root = Path(td.name)
        (root / "_data").mkdir()
        (root / "untexed" / "260904").mkdir(parents=True)
        (root / "untexed" / "260905").mkdir(parents=True)
        (root / "untexed" / "260906").mkdir(parents=True)
        data = {
            "latest_date": "260905",
            "dates": ["260905", "260904"],
            "records": {
                "260904": {"note": "Older note", "baseline": False},
                "260905": {"note": "Yesterday note", "baseline": False},
            },
        }
        with (root / "_data" / "untexed_records.yml").open("w", encoding="utf-8") as f:
            yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False)
        return td, root

    def test_union_dates_includes_new_local_snapshot_not_yet_in_yaml(self):
        td, root = self.make_repo()
        self.addCleanup(td.cleanup)
        store = daily_record.RecordStore(root)
        self.assertEqual(store.date_keys, ["260904", "260905", "260906"])
        self.assertEqual(store.latest_local_date, "260906")
        self.assertEqual(store.note_for("260906"), "")

    def test_save_historical_note_writes_yaml(self):
        td, root = self.make_repo()
        self.addCleanup(td.cleanup)
        store = daily_record.RecordStore(root)
        store.save_note("260904", "Edited historical note")
        with (root / "_data" / "untexed_records.yml").open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        self.assertEqual(data["records"]["260904"]["note"], "Edited historical note")
        self.assertFalse((root / ".daily_record_pending_note").exists())

    def test_save_latest_local_note_stages_for_builder(self):
        td, root = self.make_repo()
        self.addCleanup(td.cleanup)
        store = daily_record.RecordStore(root)
        store.save_note("260906", "New day note")
        self.assertEqual((root / ".daily_record_pending_note").read_text(encoding="utf-8"), "New day note")

    def test_clearing_latest_local_note_stages_clear_signal(self):
        td, root = self.make_repo()
        self.addCleanup(td.cleanup)
        store = daily_record.RecordStore(root)
        store.save_note("260906", "")
        self.assertEqual((root / ".daily_record_pending_note").read_text(encoding="utf-8"), "/clear")

    def test_backup_copies_yaml_before_gui_edits(self):
        td, root = self.make_repo()
        self.addCleanup(td.cleanup)
        store = daily_record.RecordStore(root)
        backup = store.backup()
        self.assertTrue(backup.exists())
        self.assertEqual(
            backup.read_text(encoding="utf-8"),
            (root / "_data" / "untexed_records.yml").read_text(encoding="utf-8"),
        )

    def test_context_rows_center_selected_date(self):
        td, root = self.make_repo()
        self.addCleanup(td.cleanup)
        store = daily_record.RecordStore(root)
        rows = store.context_rows("260905")
        self.assertEqual([row[0] for row in rows], ["260904", "260905", "260906"])
        self.assertEqual([row[2] for row in rows], [False, True, False])


if __name__ == "__main__":
    unittest.main()
