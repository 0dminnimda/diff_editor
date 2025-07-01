import sys

from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QMainWindow,
    QPlainTextEdit,
    QHBoxLayout,
)
from PySide6.QtCore import Slot


class CodePanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.editor = QPlainTextEdit(self)

    def setReadOnly(self, value: bool = True):
        self.editor.setReadOnly(value)

    def setText(self, text: str):
        self.editor.setPlainText(text)
        return self

    def verticalScrollBar(self):
        return self.editor.verticalScrollBar()


class DiffEditor(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.old = CodePanel()
        self.new = CodePanel()
        self.old.setReadOnly(True)

        self.sync_scroll_bars()

        layout = QHBoxLayout(self)
        layout.addWidget(self.old)
        layout.addWidget(self.new)

    def set_diff_text(self, old: str, new: str):
        self.old.setText(old)
        self.new.setText(new)
        return self

    def sync_scroll_bars(self):
        old_scroll_bar = self.old.verticalScrollBar()
        new_scroll_bar = self.new.verticalScrollBar()

        new_scroll_bar.valueChanged.connect(old_scroll_bar.setValue)
        old_scroll_bar.valueChanged.connect(new_scroll_bar.setValue)


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
