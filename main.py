import sys

from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QMainWindow,
    QPlainTextEdit,
    QHBoxLayout,
)
from PySide6.QtCore import Slot, QTimer


class CodePanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.editor = QPlainTextEdit(self)

    def setText(self, text: str):
        self.editor.setPlainText(text)
        return self

    def setReadOnly(self, value: bool = True):
        self.editor.setReadOnly(value)


class DiffEditor(QWidget):
    UPDATE_DELAY_MS = 300

    def __init__(self, parent=None):
        super().__init__(parent)

        self.old = CodePanel()
        self.new = CodePanel()
        self.old.setReadOnly(True)

        self._sync_scroll_bars()

        layout = QHBoxLayout(self)
        layout.addWidget(self.old)
        layout.addWidget(self.new)

        self._update_diff_when(self.new.editor.textChanged)

    def _sync_scroll_bars(self):
        old_scroll_bar = self.old.editor.verticalScrollBar()
        new_scroll_bar = self.new.editor.verticalScrollBar()

        new_scroll_bar.valueChanged.connect(old_scroll_bar.setValue)
        old_scroll_bar.valueChanged.connect(new_scroll_bar.setValue)

    def _update_diff_when(self, event):
        self.update_timer = QTimer(self)
        self.update_timer.setSingleShot(True)
        self.update_timer.setInterval(self.UPDATE_DELAY_MS)
        self.update_timer.timeout.connect(self.update_diff)

        event.connect(self.update_timer.start)

    def set_diff_text(self, old: str, new: str):
        self.old.setText(old)
        self.new.setText(new)
        return self

    def update_diff(self):
        print("updating!")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Diff Editor")
        self.resize(400, 200)

        diff_editor = DiffEditor(self)
        self.setCentralWidget(diff_editor)
        diff_editor.set_diff_text(
            "This is my custom widget!",
            "This is my custom widget!"
        )



if __name__ == "__main__":
    app = QApplication(sys.argv)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())
