#!/bin/sh
# Daily Record -> normal handwritten PDF rebuild -> normal git staging.
# Historical notes are stored in YAML; a NEW snapshot's note is staged in a
# date-bound JSON file until the build succeeds.
set -eu

REPO_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$REPO_ROOT"

if [ -x .venv/bin/python ]; then
    PYTHON=.venv/bin/python
else
    PYTHON=python3
fi

echo "Opening Daily Record..."
# Exit 3 means the user canceled the update (e.g., clicked the window X).
# All other nonzero errors also prevent the builder and git commands.
"$PYTHON" scripts/daily_record.py --repo "$REPO_ROOT"

# Existing code's DAILY_RECORD_NOTE variable is the transport into the builder.
# Only export it when the pending date matches the latest local snapshot.
if DAILY_RECORD_NOTE=$("$PYTHON" scripts/daily_record.py \
        --repo "$REPO_ROOT" --print-pending); then
    export DAILY_RECORD_NOTE
else
    STATUS=$?
    if [ "$STATUS" -ne 3 ]; then
        echo "Daily Record pending-note check failed (exit $STATUS)." >&2
        exit "$STATUS"
    fi
    unset DAILY_RECORD_NOTE
fi

echo
echo "Updating handwritten notes..."
"$PYTHON" scripts/build_untexed_records.py

# Never delete the pending note until the builder has succeeded.
"$PYTHON" scripts/daily_record.py \
    --repo "$REPO_ROOT" --clear-applied-pending

git add _data/untexed_records.yml
git add -A untexed-current/

echo
echo "Done. The normal commit/push part of update! can continue."
