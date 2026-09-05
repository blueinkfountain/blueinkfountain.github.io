# PyQt Daily Record for the Handwritten updater

This replaces the small AppleScript memo dialog with a PyQt5 window modeled on the older `Schedule Assist` program.

## Install

If you put this folder at:

```text
/Users/persist/math-blog/daily_record_note
```

run:

```bash
cd /Users/persist/math-blog
python3 /Users/persist/math-blog/daily_record_note/install.py --repo /Users/persist/math-blog
```

If PyQt5 is not already installed in the blog virtual environment:

```bash
.venv/bin/python -m pip install PyQt5
```

Then use the normal command:

```bash
update!
```

## Flow

`update!` opens the PyQt Daily Record window first. When the window closes, the normal handwritten-note builder continues automatically.

Keys:

- `Enter`: first screen -> records; then focus/save the edit line
- `Up / Down`: move to an older/newer snapshot date
- `Left / Right`: select comma-separated items, similar to the old program
- `Esc`: show `Good Luck today` and close

The GUI reads and edits `record["note"]` in `_data/untexed_records.yml`.
For a brand-new latest snapshot that is not yet in YAML, it stages the note in `.daily_record_pending_note`; `update-notes.sh` passes that value into the builder as `DAILY_RECORD_NOTE`.

A local backup of `_data/untexed_records.yml` is created when the GUI starts under `.daily_record_backup/`. Both temporary paths are added to `.gitignore`.

The installer backs up modified repo files once using the suffix:

```text
.before-pyqt-daily-record
```
