#!/bin/sh
set -e

if [ -x ".venv/bin/python" ]; then
    PYTHON=".venv/bin/python"
else
    PYTHON="python3"
fi

echo "Updating handwritten notes..."

"$PYTHON" scripts/build_untexed_records.py

git add _data/untexed_records.yml
git add -A untexed-current/

echo
echo "Done."
echo "You can now commit normally."