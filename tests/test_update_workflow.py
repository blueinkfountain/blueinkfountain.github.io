import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import yaml

ROOT = Path(__file__).resolve().parents[1]



class UpdateWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name)
        (self.repo / 'scripts').mkdir()
        (self.repo / '.venv' / 'bin').mkdir(parents=True)
        (self.repo / 'untexed-current').mkdir()
        (self.repo / 'untexed' / '261011').mkdir(parents=True)
        (self.repo / '_data').mkdir()
        (self.repo / '_data' / 'untexed_records.yml').write_text(
            yaml.safe_dump({'latest_date': '261010', 'records': {'261010': {'note': 'last'}}}),
            encoding='utf-8'
        )
        (self.repo / '.gitignore').write_text('untexed/\n')
        (self.repo / 'update-notes.sh').write_text('#!/bin/sh\necho original shell\n')
        (self.repo / 'scripts' / 'daily_record.py').write_text('print("original editor")\n')
        (self.repo / 'scripts' / 'build_untexed_records.py').write_text(
            'import os,sys\n'
            'open("builder_ran", "w").write(repr(os.environ.get("DAILY_RECORD_NOTE")))\n'
            'sys.exit(int(os.environ.get("BUILDER_EXIT", "0")))\n'
            '# DAILY_RECORD_NOTE compatibility\n'
        )
        # GUI path is stubbed but CLI --print-pending executes real program.
        wrapper = f'''#!/bin/sh
if [ "$1" = "scripts/daily_record.py" ]; then
    case "$*" in
        *--print-pending*|*--clear-applied-pending*) ;;
        *) exit "${{GUI_EXIT:-0}}" ;;
    esac
fi
exec "{sys.executable}" "$@"
'''
        binpath = self.repo / '.venv' / 'bin' / 'python'
        binpath.write_text(wrapper)
        binpath.chmod(0o755)
        subprocess.run(['git', 'init', '-q', str(self.repo)], check=True)

    def install(self):
        shutil.copy2(ROOT / 'scripts/note_storage.py', self.repo / 'scripts/note_storage.py')
        shutil.copy2(ROOT / 'scripts/daily_record.py', self.repo / 'scripts/daily_record.py')
        shutil.copy2(ROOT / 'update-notes.sh', self.repo / 'update-notes.sh')

    def run_update(self, **kwargs):
        env = {**os.environ, **kwargs}
        return subprocess.run(
            ['/bin/sh', 'update-notes.sh'], cwd=self.repo,
            env=env, capture_output=True, text=True,
        )

    def test_cancelled_gui_does_not_run_builder(self):
        self.install()
        result = self.run_update(GUI_EXIT='3')
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.repo / 'builder_ran').exists())

    def test_failed_builder_keeps_staged_note(self):
        self.install()
        pending = self.repo / '.daily_record_pending.json'
        pending.write_text(json.dumps({'date': '261011', 'note': 'Read RCA'}))
        result = self.run_update(BUILDER_EXIT='12')
        self.assertEqual(result.returncode, 12, result.stdout + result.stderr)
        self.assertTrue(pending.exists())
        self.assertEqual((self.repo / 'builder_ran').read_text(), repr('Read RCA'))

    def test_success_builder_consumes_staged_note(self):
        self.install()
        pending = self.repo / '.daily_record_pending.json'
        pending.write_text(json.dumps({'date': '261011', 'note': 'Read RCA'}))
        result = self.run_update()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse(pending.exists())
        self.assertEqual((self.repo / 'builder_ran').read_text(), repr('Read RCA'))

if __name__ == '__main__':
    unittest.main()
