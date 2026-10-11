# Daily Record — repaired version

This package replaces **only**:

- `scripts/daily_record.py` (the PyQt5 editor)
- `update-notes.sh` (launch/editor → build → stage)
- `.gitignore` (two local-only temporary/backup paths)

The installer **does not change** `scripts/build_untexed_records.py`, the ink algorithm,
`Untexed.md`, or previous Record data. The existing builder must already support
`DAILY_RECORD_NOTE`, as your current version does.

## 1. Install (macOS)

Unzip `daily_record_fixed.zip`, and put the resulting `daily_record_fixed` folder
under `/Users/persist/math-blog/daily_record_note` (or anywhere you prefer).

```bash
cd /Users/persist/math-blog

python3 /Users/persist/math-blog/daily_record_note/daily_record_fixed/install_daily_record_fix.py \
  --repo /Users/persist/math-blog
```

> If you unzip directly **inside** `daily_record_note` without the inner
> `daily_record_fixed` folder, remove `/daily_record_fixed` from the command.

Your existing `update!` shell alias remains unchanged.

## 2. Run

```bash
update!
```

If PyQt5 is not installed in `.venv`, use:

```bash
.venv/bin/python -m pip install PyQt5
```

The editor opens before the PDF build.

### Keys

- **Enter** from welcome screen: open records
- **Enter** from records: start editing the selected date
- **Enter** while editing: save the note
- **Up/Down** outside editing: select older/newer existing Record/snapshot
- **Left/Right** outside editing: highlight comma-delimited items
- **Escape** while editing: discard only unsaved typing
- **Escape** outside editing: finish and continue the normal `update!` build
- **Window X**: ask to cancel the update (the PDF builder will not run)

Notes already saved with Enter are persisted, even if you cancel a later update.

### New snapshot not yet in YAML

The editor writes `.daily_record_pending.json`, containing `{date, note}`.
This note appears immediately in the UI, survives reopening, and cannot be
accidentally applied to the wrong snapshot date. `update-notes.sh` passes it to
the existing builder **only if the date matches the newest local snapshot**.
It is deleted only **after the builder succeeds**.

If a previous run failed and the newest snapshot has changed, the editor will
preserve the old pending note rather than overwrite it. Inspect the local
`.daily_record_pending.json` to recover/migrate that note.

### Historical dates

Existing Record notes are edited in YAML. YAML updates are atomic and a backup
is created on the **first YAML edit of the session**, rather than every time
the window is opened. Backups go to `.daily_record_backup/`.

Older local snapshot folders which have no corresponding YAML Record are not
writable: the rolling builder ignores them, so writing to them would silently
lose notes.

### Formatting and restrictions

- `Today` is the actual calendar date; `Latest snapshot` is shown separately.
- Dates in the editor are recorded snapshot dates, not a calendar day picker.
- The literal string `/clear` is reserved for backward compatibility with the
  builder. To clear a note, delete all text and press Enter.
- PyQt5 and the custom `NeoDunggeunmo` font are needed to reproduce the original
  look. Qt falls back to an installed font if the custom font is unavailable.

## 3. Safety and rollback

The installer saves the originals once:

```
scripts/daily_record.py.before-record-fix
update-notes.sh.before-record-fix
.gitignore.before-record-fix
```

To restore the original editor/updater:

```bash
cd /Users/persist/math-blog
cp scripts/daily_record.py.before-record-fix scripts/daily_record.py
cp update-notes.sh.before-record-fix update-notes.sh
chmod +x update-notes.sh
```

The old `.daily_record_pending_note` file is **not** touched by the installer.
You can inspect it before deleting/migrating an unfinished update.

For safety, check `git status` before `update!` commits the new code; if your
`daily_record_note/` installation folder is inside the repository, avoid
committing temporary copies of installer packages unnecessarily.

## 4. Tests

Headless data and shell integration tests:

```bash
python3 -m unittest discover \
  -s /Users/persist/math-blog/daily_record_note/daily_record_fixed/tests -v
```

The test suite requires PyYAML, Python 3.10+, and Git. It does not require
PyQt5 because the GUI imports Qt lazily. UI interaction on macOS must be
checked by opening the app.
