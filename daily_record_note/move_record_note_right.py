from pathlib import Path
import argparse
import shutil
import re

LATEST_NOTE_INLINE = 'Record{% if latest_record.note %}<span class="record-daily-note">: {{ latest_record.note | escape }}</span>{% endif %}'
PREV_NOTE_INLINE = 'Record{% if version_record %}{% if version_record.note %}<span class="record-daily-note">: {{ version_record.note | escape }}</span>{% endif %}{% endif %}'

LATEST_NOTE_RIGHT = """          {% if latest_record.note %}
            <span class="record-daily-note">
              — {{ latest_record.note | escape }}
            </span>
          {% endif %}

"""

PREVIOUS_SUMMARY_NOTE_RIGHT = """                    {% if version_record.note %}
                      <span class="record-daily-note">
                        — {{ version_record.note | escape }}
                      </span>
                    {% endif %}

"""

def patch_latest(text):
    # Remove the old "Record: note" placement.
    text = text.replace(LATEST_NOTE_INLINE, "Record", 1)

    marker = "  Latest Record"
    pos = text.find(marker)
    if pos < 0:
        raise RuntimeError("Could not find Latest Record section.")

    # Insert after +ink and all added/modified/moved/removed counts.
    endunless = text.find("        {% endunless %}", pos)
    if endunless < 0:
        raise RuntimeError("Could not find Latest Record endunless.")

    area = text[pos:endunless]
    if "— {{ latest_record.note | escape }}" not in area:
        text = text[:endunless] + LATEST_NOTE_RIGHT + text[endunless:]

    return text

def patch_previous(text):
    # Remove the old note from the inner expanded "Record" heading.
    text = text.replace(PREV_NOTE_INLINE, "Record", 1)

    # Put the note on the Previous date summary itself, after
    # +ink and all added/modified/moved/removed counts.
    marker = '<summary class="version-summary">'
    pos = text.find(marker)
    if pos < 0:
        raise RuntimeError("Could not find Previous version summary.")

    # The first {% else %} after version-summary is the baseline branch,
    # so inserting immediately before it puts the note at the far right
    # of the non-baseline summary.
    else_pos = text.find("                  {% else %}", pos)
    if else_pos < 0:
        raise RuntimeError("Could not find Previous version baseline branch.")

    area = text[pos:else_pos]
    if "— {{ version_record.note | escape }}" not in area:
        text = text[:else_pos] + PREVIOUS_SUMMARY_NOTE_RIGHT + text[else_pos:]

    return text

def patch_css(text):
    replacement = """.record-daily-note {
  display: inline-block;
  margin-left: 0.65rem;
  font-weight: normal;
  color: #666;
  overflow-wrap: anywhere;
}"""

    pattern = re.compile(r"\.record-daily-note\s*\{.*?\}", re.S)
    if pattern.search(text):
        return pattern.sub(replacement, text, count=1)

    marker = """/* =====================================================
   Latest Record
   ===================================================== */"""
    if marker not in text:
        raise RuntimeError("Could not find Latest Record CSS marker.")
    return text.replace(marker, replacement + "\n\n\n" + marker, 1)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default=".")
    args = parser.parse_args()

    repo = Path(args.repo).expanduser().resolve()
    page = repo / "docs" / "Works" / "Untexed.md"

    if not page.exists():
        raise SystemExit(f"Missing: {page}")

    backup = page.with_name(page.name + ".before-note-right")
    if not backup.exists():
        shutil.copy2(page, backup)

    text = page.read_text(encoding="utf-8")
    text = patch_latest(text)
    text = patch_previous(text)
    text = patch_css(text)
    page.write_text(text, encoding="utf-8")

    print("Moved Daily Record notes to the far right of summary statistics.")
    print(f"Patched: {page}")
    print(f"Backup : {backup}")
    print()
    print("Now run:")
    print("  update!")

if __name__ == "__main__":
    main()
