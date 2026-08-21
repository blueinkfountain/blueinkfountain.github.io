#!/bin/sh
set -e

if [ -x ".venv/bin/python" ]; then
    PYTHON=".venv/bin/python"
else
    PYTHON="python3"
fi

# =========================================================
# Daily Record note
#
# macOS: show a text-entry dialog.
# Other systems: fall back to a terminal prompt.
#
# Empty input = keep today's existing note.
# /clear      = remove today's note.
# Cancel      = abort update!.
# =========================================================

if command -v osascript >/dev/null 2>&1; then
    DAILY_RECORD_NOTE="$(
        osascript <<'APPLESCRIPT'
try
    set dialogResult to display dialog ¬
        "What happened today?" ¬
        default answer "" ¬
        buttons {"Cancel", "OK"} ¬
        default button "OK" ¬
        cancel button "Cancel" ¬
        with title "Daily Record"

    return text returned of dialogResult

on error number -128
    return "__BLUEINK_CANCEL__"
end try
APPLESCRIPT
    )"

    if [ "$DAILY_RECORD_NOTE" = "__BLUEINK_CANCEL__" ]; then
        echo "Update cancelled."
        exit 1
    fi
else
    printf "Daily Record (Enter = keep, /clear = remove): "
    IFS= read -r DAILY_RECORD_NOTE
fi

export DAILY_RECORD_NOTE

echo
echo "Updating handwritten notes..."

"$PYTHON" scripts/build_untexed_records.py

git add _data/untexed_records.yml
git add -A untexed-current/

echo
echo "Done."
echo "You can now commit normally."