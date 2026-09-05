from pathlib import Path
from datetime import datetime
import argparse
import sys
import shutil
import yaml


DATE_FMT = "%y%m%d"
DISPLAY_FMT = "%Y-%m-%d"
PENDING_FILE = ".daily_record_pending_note"


class RecordStore:
    def __init__(self, repo_root):
        self.repo_root = Path(repo_root).expanduser().resolve()
        self.yaml_path = self.repo_root / "_data" / "untexed_records.yml"
        self.snapshot_root = self.repo_root / "untexed"
        self.pending_path = self.repo_root / PENDING_FILE
        self.data = self._load_yaml()
        self.records = self.data.setdefault("records", {})
        self.date_keys = self._collect_date_keys()
        self.latest_local_date = self._latest_local_date()

    def _load_yaml(self):
        if not self.yaml_path.exists():
            return {"latest_date": None, "dates": [], "records": {}}
        with self.yaml_path.open("r", encoding="utf-8") as handle:
            loaded = yaml.safe_load(handle) or {}
        loaded.setdefault("records", {})
        loaded.setdefault("dates", [])
        return loaded

    @staticmethod
    def _is_date_key(value):
        text = str(value)
        if len(text) != 6 or not text.isdigit():
            return False
        try:
            datetime.strptime(text, DATE_FMT)
        except ValueError:
            return False
        return True

    def _local_date_keys(self):
        if not self.snapshot_root.exists():
            return []
        return sorted(
            path.name
            for path in self.snapshot_root.iterdir()
            if path.is_dir() and self._is_date_key(path.name)
        )

    def _collect_date_keys(self):
        known = set()
        known.update(str(key) for key in self.records if self._is_date_key(key))
        known.update(str(key) for key in self.data.get("dates", []) if self._is_date_key(key))
        known.update(self._local_date_keys())
        return sorted(known)

    def _latest_local_date(self):
        local = self._local_date_keys()
        if local:
            return local[-1]
        if self.date_keys:
            return self.date_keys[-1]
        return None

    @staticmethod
    def display_date(date_key):
        return datetime.strptime(str(date_key), DATE_FMT).strftime(DISPLAY_FMT)

    def note_for(self, date_key):
        record = self.records.get(str(date_key)) or {}
        return str(record.get("note", "") or "")

    def save_note(self, date_key, note):
        date_key = str(date_key)
        note = str(note).strip()

        if date_key == self.latest_local_date:
            self.pending_path.write_text(note if note else "/clear", encoding="utf-8")

        if date_key in self.records:
            self.records[date_key]["note"] = note
            self._write_yaml()

    def _write_yaml(self):
        self.yaml_path.parent.mkdir(parents=True, exist_ok=True)
        with self.yaml_path.open("w", encoding="utf-8") as handle:
            yaml.safe_dump(
                self.data,
                handle,
                allow_unicode=True,
                sort_keys=False,
                width=180,
            )

    def backup(self):
        if not self.yaml_path.exists():
            return None
        backup_dir = self.repo_root / ".daily_record_backup"
        backup_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S-%f")
        destination = backup_dir / f"untexed_records_{stamp}.yml"
        shutil.copy2(self.yaml_path, destination)
        return destination

    def context_rows(self, selected_key, radius=1):
        if not self.date_keys:
            return []
        try:
            index = self.date_keys.index(str(selected_key))
        except ValueError:
            index = len(self.date_keys) - 1
        start = max(0, index - radius)
        end = min(len(self.date_keys), index + radius + 1)
        rows = []
        for key in self.date_keys[start:end]:
            rows.append((key, self.note_for(key), key == str(selected_key)))
        return rows

    def previous_key(self, selected_key):
        if not self.date_keys:
            return None
        try:
            index = self.date_keys.index(str(selected_key))
        except ValueError:
            return self.date_keys[-1]
        return self.date_keys[max(0, index - 1)]

    def next_key(self, selected_key):
        if not self.date_keys:
            return None
        try:
            index = self.date_keys.index(str(selected_key))
        except ValueError:
            return self.date_keys[-1]
        return self.date_keys[min(len(self.date_keys) - 1, index + 1)]


class MissingPyQt(RuntimeError):
    pass


def run_gui(repo_root):
    try:
        from PyQt5.QtWidgets import (
            QApplication,
            QMainWindow,
            QLabel,
            QVBoxLayout,
            QWidget,
            QLineEdit,
        )
        from PyQt5.QtCore import QDate, Qt, QTime, QTimer
        from PyQt5.QtGui import QFont
    except ImportError as exc:
        raise MissingPyQt(
            "PyQt5 is required. Install it in the blog virtual environment with: "
            ".venv/bin/python -m pip install PyQt5"
        ) from exc

    store = RecordStore(repo_root)
    store.backup()

    class TypingLabel(QLabel):
        def __init__(self, text, parent=None, speed=22):
            super().__init__(parent)
            self.setFont(QFont("NeoDunggeunmo", 14))
            self.setAlignment(Qt.AlignCenter)
            self.setWordWrap(True)
            self.full_text = text
            self.current_text = ""
            self.current_index = 0
            self.speed = speed
            self.timer = QTimer(self)
            self.timer.timeout.connect(self.advance)
            self.timer.start(self.speed)

        def advance(self):
            if self.current_index >= len(self.full_text):
                self.timer.stop()
                return
            ch = self.full_text[self.current_index]
            self.current_text += ch
            self.setText(self.current_text)
            self.current_index += 1
            delay = self.speed * (3 if ch in ",.!?'" else 1)
            self.timer.setInterval(delay)

    class DailyRecordWindow(QMainWindow):
        def __init__(self):
            super().__init__()
            self.store = store
            self.selected_key = (
                self.store.latest_local_date
                or (self.store.date_keys[-1] if self.store.date_keys else None)
            )
            self.mode = "first"
            self.item_select = 0
            self.input_focused = False
            self.saved_anything = False
            self.setWindowTitle("Schedule Assist")
            self.setFont(QFont("NeoDunggeunmo", 15))
            self.setFixedSize(500, 500)
            self._build_shell()
            self._start_clock()
            self.show_first()

        def _build_shell(self):
            self.central = QWidget(self)
            self.layout = QVBoxLayout(self.central)
            self.layout.setContentsMargins(22, 22, 22, 22)
            self.layout.setSpacing(14)
            self.setCentralWidget(self.central)

        def _start_clock(self):
            self.status_bar = self.statusBar()
            self.clock = QTimer(self)
            self.clock.timeout.connect(self.update_time)
            self.clock.start(1000)
            self.update_time()

        def update_time(self):
            date = QDate.currentDate().toString(Qt.ISODate)
            time = QTime.currentTime().toString("AP h:mm:ss")
            self.status_bar.showMessage(f"{date} {time}")

        def clear_layout(self):
            while self.layout.count():
                item = self.layout.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()

        def first_text(self):
            today_key = self.selected_key
            today_display = (
                self.store.display_date(today_key)
                if today_key else datetime.now().strftime(DISPLAY_FMT)
            )
            today_note = self.store.note_for(today_key) if today_key else ""
            previous_key = self.store.previous_key(today_key) if today_key else None
            yesterday_note = self.store.note_for(previous_key) if previous_key else ""
            return (
                f"Good day.\n\n"
                f"Today is {today_display}.\n\n"
                f"Yesterday, you did {yesterday_note or 'Nothing'}.\n"
                f"Today, you did {today_note or 'Nothing'}.\n\n"
                "Press Enter to Continue."
            )

        def show_first(self):
            self.mode = "first"
            self.clear_layout()
            label = TypingLabel(self.first_text(), self, speed=20)
            label.setAlignment(Qt.AlignCenter)
            self.layout.addWidget(label)

        def formatted_context(self):
            lines = []
            for key, note, selected in self.store.context_rows(self.selected_key, radius=2):
                prefix = "- " if selected else "  "
                display = self.store.display_date(key)
                shown_note = note or " "
                if selected and self.item_select > 0 and shown_note.strip():
                    parts = [part.strip() for part in shown_note.split(",")]
                    idx = min(self.item_select - 1, len(parts) - 1)
                    parts[idx] = "- " + parts[idx]
                    shown_note = ", ".join(parts)
                lines.append(f"{prefix}{display}   {shown_note}")
            return "\n".join(lines)

        def show_records(self):
            self.mode = "records"
            self.input_focused = False
            self.clear_layout()
            label = TypingLabel(self.formatted_context(), self, speed=8)
            label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            self.layout.addWidget(label)

            self.status_input = QLineEdit(self)
            self.status_input.setText(self.store.note_for(self.selected_key))
            self.status_input.setFocusPolicy(Qt.NoFocus)
            self.status_input.returnPressed.connect(self.save_input)
            self.layout.addWidget(self.status_input)

            hint = QLabel("Enter: edit/save   ↑↓: date   ←→: item   Esc: finish", self)
            hint.setFont(QFont("NeoDunggeunmo", 10))
            hint.setAlignment(Qt.AlignCenter)
            self.layout.addWidget(hint)

        def save_input(self):
            text = self.status_input.text().strip()
            self.store.save_note(self.selected_key, text)
            self.saved_anything = True
            self.input_focused = False
            self.item_select = 0
            self.show_records()

        def focus_input(self):
            self.status_input.setFocusPolicy(Qt.StrongFocus)
            self.status_input.setFocus()
            self.input_focused = True

        def move_date(self, older):
            if self.input_focused:
                return
            new_key = (
                self.store.previous_key(self.selected_key)
                if older
                else self.store.next_key(self.selected_key)
            )
            if new_key and new_key != self.selected_key:
                self.selected_key = new_key
                self.item_select = 0
                self.show_records()

        def move_item(self, direction):
            if self.input_focused:
                return
            note = self.store.note_for(self.selected_key)
            parts = [part for part in note.split(",") if part.strip()]
            if not parts:
                self.item_select = 0
            else:
                self.item_select = max(
                    0,
                    min(len(parts), self.item_select + direction),
                )
            self.show_records()

        def finish(self):
            self.clear_layout()
            label = TypingLabel("Good Luck today", self, speed=24)
            label.setAlignment(Qt.AlignCenter)
            self.layout.addWidget(label)
            QTimer.singleShot(1000, self.close)

        def keyPressEvent(self, event):
            key = event.key()
            if key in (Qt.Key_Return, Qt.Key_Enter):
                if self.mode == "first":
                    self.show_records()
                    return
                if self.mode == "records" and not self.input_focused:
                    self.focus_input()
                    return
            elif key == Qt.Key_Escape:
                self.finish()
                return
            elif self.mode == "records" and key == Qt.Key_Up:
                self.move_date(older=True)
                return
            elif self.mode == "records" and key == Qt.Key_Down:
                self.move_date(older=False)
                return
            elif self.mode == "records" and key == Qt.Key_Left:
                self.move_item(-1)
                return
            elif self.mode == "records" and key == Qt.Key_Right:
                self.move_item(1)
                return
            super().keyPressEvent(event)

    app = QApplication(sys.argv)
    window = DailyRecordWindow()
    window.show()
    return app.exec_()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default=".")
    args = parser.parse_args()
    try:
        return run_gui(args.repo)
    except MissingPyQt as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
