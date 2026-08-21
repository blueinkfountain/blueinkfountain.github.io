Daily Record note feature

Install from your repository root:

  cd /Users/persist/math-blog
  python3 /PATH/TO/daily_record_note/install_daily_record_note.py

Then run:

  update!

Behavior:
- macOS shows a text-entry dialog.
- typed text is stored in _data/untexed_records.yml as the latest Record's `note`.
- latest page shows: Record: <your text>
- Previous historical Records keep and show their own note.
- Enter with no text keeps the existing note.
- Type /clear to remove the latest note.
- Cancel aborts update! before any regeneration/commit.

The installer backs up all three touched files before changing them.
