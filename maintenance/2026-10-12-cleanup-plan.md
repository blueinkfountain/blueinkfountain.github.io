# Math blog maintenance implementation plan

> Execution: superpowers:executing-plans; tests first for behavioral changes.

## Goal and approved design
Implement the user's approved review recommendations after a complete verified backup.
Keep the Jekyll site, published URLs, original mathematics, frozen history and local snapshots.
Use scripts/ and assets/euler-method/ as canonical sources; tests/ exercises these sources.
No automatic push/deployment. Work in the current checkout as requested; preserve pre-existing changes.

## Backup
/Users/persist/math-blog-backups/2026-10-12-before-cleanup/math-blog
19,306 regular files; 6,068,413,017 bytes; 22,032 entries including directories and symlinks.
All SHA-256 contents and symlink targets match. Full manifest: ../verification.json in backup directory.

## Tasks
- [x] 1. Repair navigation/PDF targets/control filenames, preserving URL compatibility where feasible. Add scripts/check_site.py and tests/test_site_validation.py for missing/case-sensitive paths, missing parents, malformed names, and PDF metadata.
- [x] 2. Consolidate real-code tests under tests/, archive old installers/backups, move fonts out of PDF directory, exclude development files from publication. Keep original PDFs and snapshot dates.
- [x] 3. Add _layouts/pdf.html and assets/css/site.css. Convert PDF wrappers to metadata, retain substantive text, restore solution indexes, responsive sidebar and correct MathJax initialization order.
- [x] 4. Add scripts/note_storage.py for content/config-keyed cache and staged recoverable PDF/YAML publication. Integrate with builder preserving existing math calculations. Test unchanged reuse, invalidation, changed PDFs, failures, interruption recovery, frozen history.
- [x] 5. Document setup/update/recovery; pin Python dependencies; run Python/Node tests and link validation on PR and before deployment; build/render Jekyll and inspect mobile/desktop.

## Review focus
- Existing URLs and case-sensitive Linux filesystem must remain valid.
- Missing PDFs must not be silently substituted with unrelated content.
- Cache invalidation includes renderer/algorithm parameters and reference PDF content.
- Failure during publication must not destroy the previous PDF/YAML pair or pending note.
- Existing frozen history and original PDFs must remain byte-for-byte unchanged by housekeeping.

## Verification
Python: .venv/bin/python -m unittest discover -s tests -p 'test_*.py'
JavaScript: node --test tests/*.test.mjs
Content: .venv/bin/python scripts/check_site.py
Build: bundle exec jekyll build (isolated local gems if necessary).

## Ledger
- Backup copied with ditto; full independent checksum comparison passed before project edits.
- Ruling: execute in the requested current folder to include the user's uncommitted package replacement and local-only snapshots; backup provides complete rollback.
- Ruling: user explicitly approved all proposed improvements and execution; no additional design approval needed.
- Tasks 1–4 implemented; tests: 31 Python + 34 Node passing before final build validation.
- Independent review found recovery ordering bug: Daily Record opened before transaction rollback. Added failing real-editor regression and moved recovery under lock before GUI/CLI history access; now passes.
- Existing public PDFs (228 handwritten + 91 assets + 15 solutions), record YAML and calibration PDFs compare byte-identically with backup.
- Two malformed control-character document URLs replaced with clean filenames; preserving those invalid URL bytes would recreate the original defect.
- Theme now uses the just-the-docs gem locked with all its dependencies; remote-theme downloads were exposing undeclared dependency failures in actual builds.
- A new ode_lab_dynamics_upgrade/ folder appeared externally after backup. Left its contents untouched and excluded it from publication as an installation package; it was not in the initial backup.

- Final: 34 Python + 34 Node tests; Jekyll build and emitted-site validation passed. Independent follow-up review found no additional major issues. See 2026-10-12-results.md for evidence and limits.
