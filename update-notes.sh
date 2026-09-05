#!/bin/sh
set -e

if [ -x ".venv/bin/python" ]; then
    PYTHON=".venv/bin/python"
else
    PYTHON="python3"
fi

# Fresh run: never reuse a stale note from a previously interrupted update.
rm -f .daily_record_pending_note

echo "Opening Daily Record..."
"$PYTHON" scripts/daily_record.py --repo "$PWD"

if [ -f .daily_record_pending_note ]; then
    DAILY_RECORD_NOTE="$(cat .daily_record_pending_note)"
    export DAILY_RECORD_NOTE
fi

echo
echo "Updating handwritten notes..."
"$PYTHON" scripts/build_untexed_records.py

rm -f .daily_record_pending_note

git add _data/untexed_records.yml
git add -A untexed-current/

echo
echo "Done."
echo "You can now commit normally."
