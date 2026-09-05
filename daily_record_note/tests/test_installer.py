from pathlib import Path
import importlib.util
import tempfile
import unittest

INSTALLER_PATH = Path(__file__).resolve().parents[1] / "install.py"
spec = importlib.util.spec_from_file_location("installer", INSTALLER_PATH)
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class InstallerTests(unittest.TestCase):
    def make_repo(self):
        td = tempfile.TemporaryDirectory()
        root = Path(td.name)
        (root / "scripts").mkdir()
        (root / "_data").mkdir()
        (root / ".gitignore").write_text("untexed/\n", encoding="utf-8")
        (root / "update-notes.sh").write_text("#!/bin/sh\necho old\n", encoding="utf-8")
        builder = '''from pathlib import Path\nimport yaml\n\ndef main():\n    existing_records = {}\n    records = {}\n    latest_date = "260906"\n    # =====================================================\n    # Sort Added / Modified by ink amount for display\n    # =====================================================\n    pass\n'''
        (root / "scripts" / "build_untexed_records.py").write_text(builder, encoding="utf-8")
        return td, root

    def test_install_adds_gui_shell_flow_and_note_preservation(self):
        td, root = self.make_repo()
        self.addCleanup(td.cleanup)
        installer.install(root, Path(__file__).resolve().parents[1])

        shell = (root / "update-notes.sh").read_text(encoding="utf-8")
        builder = (root / "scripts" / "build_untexed_records.py").read_text(encoding="utf-8")
        ignore = (root / ".gitignore").read_text(encoding="utf-8")

        self.assertTrue((root / "scripts" / "daily_record.py").exists())
        self.assertLess(shell.index("scripts/daily_record.py"), shell.index("scripts/build_untexed_records.py"))
        self.assertIn('DAILY_RECORD_NOTE="$(cat .daily_record_pending_note)"', shell)
        self.assertIn("export DAILY_RECORD_NOTE", shell)
        self.assertIn("# Daily Record note", builder)
        self.assertIn('os.environ.get("DAILY_RECORD_NOTE")', builder)
        self.assertIn(".daily_record_pending_note", ignore)

    def test_install_is_idempotent(self):
        td, root = self.make_repo()
        self.addCleanup(td.cleanup)
        package = Path(__file__).resolve().parents[1]
        installer.install(root, package)
        installer.install(root, package)
        builder = (root / "scripts" / "build_untexed_records.py").read_text(encoding="utf-8")
        ignore = (root / ".gitignore").read_text(encoding="utf-8")
        self.assertEqual(builder.count("# Daily Record note"), 1)
        self.assertEqual(ignore.count(".daily_record_pending_note"), 1)


if __name__ == "__main__":
    unittest.main()
