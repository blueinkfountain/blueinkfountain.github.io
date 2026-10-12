"""Daily Record editor for the Blueink Jekyll handwritten-notes history.

Historical notes are written to YAML atomically. A note for the latest
snapshot when it has not yet been generated is staged with its exact date;
normal update! applies it only to that same snapshot date.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile

import yaml
from note_storage import build_lock, recover_publication

DATE_FMT = "%y%m%d"
DISPLAY_FMT = "%Y-%m-%d"
PENDING_FILE = ".daily_record_pending.json"


def atomic_text_write(path: Path, text: str) -> None:
    """Replace a file atomically, without risking an empty/truncated YAML."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent,
            prefix=f".{path.name}.", suffix=".tmp", delete=False,
        ) as handle:
            tmp_path = Path(handle.name)
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        if path.exists():
            os.chmod(tmp_path, path.stat().st_mode)
        os.replace(tmp_path, path)
    finally:
        if tmp_path is not None:
            tmp_path.unlink(missing_ok=True)


class RecordStore:
    def __init__(self, repo_root: str | Path):
        self.repo_root = Path(repo_root).expanduser().resolve()
        self.yaml_path = self.repo_root / "_data" / "untexed_records.yml"
        self.snapshot_root = self.repo_root / "untexed"
        self.pending_path = self.repo_root / PENDING_FILE
        self.data = self._load_yaml()
        self.records = self.data["records"]
        self.latest_local_date = self._latest_snapshot_date()
        self.pending = self._load_pending()
        self._backup_created = False
        # An older local snapshot not in YAML is NOT writable: the normal
        # rolling builder will never create a historical Record for it.
        known = {str(k) for k in self.records if self._valid_date(k)}
        if self.latest_local_date is not None:
            known.add(self.latest_local_date)
        self.date_keys = sorted(known)

    @staticmethod
    def _valid_date(value) -> bool:
        key = str(value)
        if len(key) != 6 or not key.isdigit():
            return False
        try:
            datetime.strptime(key, DATE_FMT)
            return True
        except ValueError:
            return False

    def _load_yaml(self) -> dict:
        if not self.yaml_path.is_file():
            raise FileNotFoundError(f"Record history not found: {self.yaml_path}")
        with self.yaml_path.open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}
        if not isinstance(data, dict) or not isinstance(data.get("records"), dict):
            raise ValueError("untexed_records.yml has no valid records mapping")
        return data

    def _latest_snapshot_date(self) -> str | None:
        if not self.snapshot_root.is_dir():
            return None
        keys = [
            p.name for p in self.snapshot_root.iterdir()
            if p.is_dir() and self._valid_date(p.name)
        ]
        return max(keys) if keys else None

    def _load_pending(self) -> dict | None:
        if not self.pending_path.is_file():
            return None
        try:
            data = json.loads(self.pending_path.read_text(encoding="utf-8"))
        except (OSError, ValueError, RuntimeError) as exc:
            raise ValueError(f"Pending note is corrupted: {self.pending_path}") from exc
        if (not isinstance(data, dict)
                or not self._valid_date(data.get("date"))
                or not isinstance(data.get("note"), str)):
            raise ValueError(f"Pending note has an invalid format: {self.pending_path}")
        return data

    @staticmethod
    def display_date(key: str) -> str:
        return datetime.strptime(str(key), DATE_FMT).strftime(DISPLAY_FMT)

    def note_for(self, key: str | None) -> str:
        if key is None:
            return ""
        key = str(key)
        if self.pending and self.pending["date"] == key:
            return self.pending["note"]
        return str((self.records.get(key) or {}).get("note", "") or "")

    def pending_for_latest(self) -> str | None:
        if not self.pending or self.pending["date"] != self.latest_local_date:
            return None
        return self.pending["note"] if self.pending["note"] else "/clear"

    def clear_applied_pending(self) -> None:
        if self.pending_for_latest() is not None:
            self.pending_path.unlink(missing_ok=True)
            self.pending = None

    def save_note(self, key: str, note: str) -> None:
        key = str(key)
        if key not in self.date_keys:
            raise ValueError(f"Date {key} is not editable: no stored Record or newest snapshot")
        note = str(note).strip()
        # Existing builder reserves /clear as a transport token.
        if note == "/clear":
            raise ValueError("The text /clear is reserved. Leave the field empty to clear a note.")

        if key in self.records:
            self._backup_before_first_yaml_edit()
            self.records[key]["note"] = note
            atomic_text_write(
                self.yaml_path,
                yaml.safe_dump(self.data, allow_unicode=True,
                               sort_keys=False, width=180),
            )
            # If an older pending exists for the same snapshot, remove it:
            # YAML has now become the authoritative source for this date.
            if self.pending and self.pending["date"] == key:
                self.pending_path.unlink(missing_ok=True)
                self.pending = None
        elif key == self.latest_local_date:
            if self.pending and self.pending["date"] != key:
                raise ValueError(
                    f"An unapplied note for {self.pending['date']} still exists in "
                    f"{self.pending_path}. Preserve or manually resolve it "
                    "before staging a different date."
                )
            self.pending = {"date": key, "note": note}
            atomic_text_write(
                self.pending_path,
                json.dumps(self.pending, ensure_ascii=False, indent=2) + "\n",
            )
        else:
            raise ValueError(f"Date {key} is not editable")

    def _backup_before_first_yaml_edit(self) -> None:
        if self._backup_created:
            return
        folder = self.repo_root / ".daily_record_backup"
        folder.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S-%f")
        shutil.copy2(self.yaml_path, folder / f"untexed_records_{stamp}.yml")
        self._backup_created = True

    def previous_key(self, key: str | None) -> str | None:
        if not self.date_keys:
            return None
        if key not in self.date_keys:
            return self.date_keys[-1]
        return self.date_keys[max(0, self.date_keys.index(key) - 1)]

    def next_key(self, key: str | None) -> str | None:
        if not self.date_keys:
            return None
        if key not in self.date_keys:
            return self.date_keys[-1]
        return self.date_keys[min(len(self.date_keys) - 1, self.date_keys.index(key) + 1)]

    def context_rows(self, key: str | None, radius: int = 2):
        if not self.date_keys:
            return []
        idx = self.date_keys.index(key) if key in self.date_keys else len(self.date_keys) - 1
        start = max(0, idx - radius)
        end = min(len(self.date_keys), idx + radius + 1)
        return [(k, self.note_for(k), k == key) for k in self.date_keys[start:end]]


def make_intro_text(store: RecordStore, current: datetime | None = None) -> str:
    now = current or datetime.now()
    today = now.strftime(DISPLAY_FMT)
    yesterday_key = (now - timedelta(days=1)).strftime(DATE_FMT)
    today_key = now.strftime(DATE_FMT)
    previous = store.note_for(yesterday_key) or "Nothing"
    today_note = store.note_for(today_key) or "Nothing"
    current_snapshot = (
        store.display_date(store.latest_local_date)
        if store.latest_local_date else "not found"
    )
    return (
        f"Good day.\n\nToday is {today}.\n\n"
        f"Yesterday, you did {previous}.\n"
        f"Today, you did {today_note}.\n\n"
        f"Latest snapshot: {current_snapshot}\n\n"
        "Press Enter to Continue."
    )


class MissingPyQt(RuntimeError):
    pass


def run_gui(repo_root: Path) -> int:
    try:
        from PyQt5.QtCore import QDate, QEvent, Qt, QTime, QTimer
        from PyQt5.QtGui import QFont
        from PyQt5.QtWidgets import (
            QApplication, QLabel, QLineEdit, QMainWindow,
            QMessageBox, QScrollArea, QVBoxLayout, QWidget,
        )
    except ImportError as exc:
        raise MissingPyQt(
            "PyQt5 is required. Install with: .venv/bin/python -m pip install PyQt5"
        ) from exc

    store = RecordStore(repo_root)

    class TypingLabel(QLabel):
        def __init__(self, text: str, parent=None, speed: int = 18):
            super().__init__(parent)
            self.setFont(QFont("NeoDunggeunmo", 13))
            self.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            self.setWordWrap(True)
            self.setTextInteractionFlags(Qt.TextSelectableByMouse)
            self.full_text = text
            self.at = 0
            self.speed = speed
            self.timer = QTimer(self)
            self.timer.timeout.connect(self.advance)
            self.timer.start(speed)

        def advance(self):
            if self.at >= len(self.full_text):
                self.timer.stop()
                return
            ch = self.full_text[self.at]
            self.at += 1
            self.setText(self.full_text[:self.at])
            self.timer.setInterval(self.speed * (3 if ch in ",.!?'" else 1))

    class NoteInput(QLineEdit):
        def __init__(self, window):
            super().__init__(window)
            self.owner = window

        def keyPressEvent(self, event):
            if event.key() in (Qt.Key_Return, Qt.Key_Enter):
                self.owner.save_input()
                event.accept()
            elif event.key() == Qt.Key_Escape:
                self.owner.cancel_input()
                event.accept()
            else:
                super().keyPressEvent(event)

    class DailyRecordWindow(QMainWindow):
        def __init__(self):
            super().__init__()
            self.selected_key = store.latest_local_date or (
                store.date_keys[-1] if store.date_keys else None
            )
            self.mode = "welcome"
            self.item_select = 0
            self.editing = False
            self.intentional_finish = False
            self.exit_status = 3  # Closing with X cancels update, not silently runs it.
            self.setWindowTitle("Schedule Assist — Daily Record")
            self.setFont(QFont("NeoDunggeunmo", 14))
            self.setFixedSize(520, 510)
            self.central = QWidget(self)
            self.layout = QVBoxLayout(self.central)
            self.layout.setContentsMargins(20, 20, 20, 20)
            self.layout.setSpacing(12)
            self.setCentralWidget(self.central)
            self.clock = QTimer(self)
            self.clock.timeout.connect(self.update_clock)
            self.clock.start(1000)
            self.update_clock()
            self.show_welcome()

        def update_clock(self):
            d = QDate.currentDate().toString(Qt.ISODate)
            t = QTime.currentTime().toString("AP h:mm:ss")
            self.statusBar().showMessage(f"{d} {t}")

        def clear_layout(self):
            while self.layout.count():
                item = self.layout.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()

        def show_text(self, text, speed, alignment):
            scroll = QScrollArea(self)
            scroll.setWidgetResizable(True)
            scroll.setFrameShape(QScrollArea.NoFrame)
            label = TypingLabel(text, self, speed=speed)
            label.setAlignment(alignment)
            scroll.setWidget(label)
            self.layout.addWidget(scroll)

        def show_welcome(self):
            self.mode = "welcome"
            self.editing = False
            self.clear_layout()
            self.show_text(make_intro_text(store), 17, Qt.AlignCenter)

        def formatted_context(self):
            lines = []
            for key, note, chosen in store.context_rows(self.selected_key):
                prefix = "- " if chosen else "  "
                note = note or " "
                if chosen and self.item_select and note.strip():
                    parts = [p.strip() for p in note.split(",")]
                    ix = min(self.item_select - 1, len(parts) - 1)
                    parts[ix] = "- " + parts[ix]
                    note = ", ".join(parts)
                lines.append(f"{prefix}{store.display_date(key)}   {note}")
            return "\n".join(lines) if lines else "No record dates available."

        def show_records(self):
            self.mode = "records"
            self.editing = False
            self.clear_layout()
            self.show_text(self.formatted_context(), 7, Qt.AlignLeft | Qt.AlignVCenter)
            self.status_input = NoteInput(self)
            self.status_input.setText(store.note_for(self.selected_key))
            self.status_input.setReadOnly(True)
            self.status_input.setFocusPolicy(Qt.NoFocus)
            self.layout.addWidget(self.status_input)
            hint = QLabel("Enter: edit/save   ↑↓: date   ←→: item   Esc: finish", self)
            hint.setFont(QFont("NeoDunggeunmo", 9))
            hint.setAlignment(Qt.AlignCenter)
            self.layout.addWidget(hint)
            if self.selected_key is None:
                self.statusBar().showMessage("No snapshot available. Close to cancel update.")

        def focus_input(self):
            if self.selected_key is None:
                return
            self.status_input.setReadOnly(False)
            self.status_input.setFocusPolicy(Qt.StrongFocus)
            self.status_input.setFocus()
            self.status_input.setCursorPosition(len(self.status_input.text()))
            self.editing = True

        def cancel_input(self):
            # Escape while typing discards unsaved text, not the whole update.
            self.show_records()

        def save_input(self):
            try:
                store.save_note(self.selected_key, self.status_input.text())
            except (OSError, ValueError, RuntimeError) as exc:
                QMessageBox.warning(self, "Save failed", str(exc))
                return
            self.item_select = 0
            self.show_records()

        def move_date(self, older):
            if self.editing:
                return
            next_key = (store.previous_key(self.selected_key) if older
                        else store.next_key(self.selected_key))
            if next_key and next_key != self.selected_key:
                self.selected_key = next_key
                self.item_select = 0
                self.show_records()

        def move_item(self, direction):
            if self.editing or self.selected_key is None:
                return
            count = len([p for p in store.note_for(self.selected_key).split(",") if p.strip()])
            self.item_select = max(0, min(count, self.item_select + direction))
            self.show_records()

        def finish(self):
            if self.mode == "finishing":
                return
            self.mode = "finishing"
            self.intentional_finish = True
            self.exit_status = 0
            self.clear_layout()
            self.show_text("Good Luck today", 22, Qt.AlignCenter)
            QTimer.singleShot(950, self.close)

        def closeEvent(self, event):
            if self.intentional_finish:
                self.exit_status = 0
                event.accept()
                return
            if self.editing:
                answer = QMessageBox.question(
                    self, "Cancel update?",
                    "Discard your unsaved text and cancel update!?",
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
                )
            else:
                answer = QMessageBox.question(
                    self, "Cancel update?",
                    "Close Daily Record and cancel update!?\n"
                    "Press Esc in the main window to finish and continue.",
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
                )
            if answer == QMessageBox.Yes:
                self.exit_status = 3
                event.accept()
            else:
                event.ignore()

        def eventFilter(self, watched, event):
            # QScrollArea consumes arrow keys for scrolling. Route the editor's
            # keyboard shortcuts here so navigation works regardless of
            # which non-editable child currently owns keyboard focus.
            if (event.type() == QEvent.KeyPress
                    and watched is not self
                    and self.mode in ("welcome", "records")
                    and not self.editing
                    and event.key() in (
                        Qt.Key_Return, Qt.Key_Enter, Qt.Key_Escape,
                        Qt.Key_Up, Qt.Key_Down, Qt.Key_Left, Qt.Key_Right,
                    )):
                self.keyPressEvent(event)
                return True
            return super().eventFilter(watched, event)

        def keyPressEvent(self, event):
            key = event.key()
            if key in (Qt.Key_Return, Qt.Key_Enter):
                if self.mode == "welcome":
                    self.show_records()
                    return
                if self.mode == "records" and not self.editing:
                    self.focus_input()
                    return
            elif key == Qt.Key_Escape:
                if self.editing:
                    self.cancel_input()
                else:
                    self.finish()
                return
            elif self.mode == "records" and not self.editing:
                if key == Qt.Key_Up:
                    self.move_date(True)
                    return
                if key == Qt.Key_Down:
                    self.move_date(False)
                    return
                if key == Qt.Key_Left:
                    self.move_item(-1)
                    return
                if key == Qt.Key_Right:
                    self.move_item(1)
                    return
            super().keyPressEvent(event)

    app = QApplication.instance() or QApplication(sys.argv)
    window = DailyRecordWindow()
    app.installEventFilter(window)
    window.show()
    app.exec_()
    app.removeEventFilter(window)
    return window.exit_status


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default=".")
    actions = parser.add_mutually_exclusive_group()
    actions.add_argument("--print-pending", action="store_true")
    actions.add_argument("--clear-applied-pending", action="store_true")
    args = parser.parse_args()

    try:
        repo = Path(args.repo).expanduser().resolve()
        with build_lock(repo):
            recover_publication(repo / "untexed-current", repo / "_data/untexed_records.yml")
            if args.print_pending or args.clear_applied_pending:
                store = RecordStore(args.repo)
                if args.print_pending:
                    pending = store.pending_for_latest()
                    if pending is None:
                        return 3
                    sys.stdout.write(pending)
                    return 0
                store.clear_applied_pending()
                return 0
            return run_gui(Path(args.repo))
    except MissingPyQt as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"Daily Record error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
