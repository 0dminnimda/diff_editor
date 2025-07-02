import sys
import signal
from pathlib import Path

from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QMainWindow,
    QPlainTextEdit,
    QHBoxLayout,
)
from PySide6.QtCore import (
    Qt,
    QTimer,
    QRect,
    QSize,
    Slot,
)
from PySide6.QtGui import QPainter, QColor, QPaintEvent


DIR = Path(__file__).parent
DARK_STYLE_SHEET_FILE = DIR/"dark_mode.qss"
# TODO: https://github.com/5yutan5/PyQtDarkTheme/blob/main/style/base.qss

if DARK_STYLE_SHEET_FILE.exists():
    DARK_STYLE_SHEET = DARK_STYLE_SHEET_FILE.read_text()
else:
    DARK_STYLE_SHEET = ""


def count_digits(x: int) -> int:
    return len(str(x)) if x > 0 else 1


def iterate_visible_blocks(editor: QPlainTextEdit):
    block = editor.firstVisibleBlock()
    block_number = block.blockNumber()
    while block.isValid() and block.isVisible():
        yield block_number, block
        block = block.next()
        block_number += 1


class LineNumbers(QWidget):
    LEFT_PADDING_PX = 15
    RIGHT_PADDING_PX = 5

    def __init__(self, editor: QPlainTextEdit):
        super().__init__(editor)
        self.editor = editor

    def calculate_width(self) -> int:
        digits = count_digits(self.editor.blockCount())
        digit_width = self.fontMetrics().horizontalAdvance('9')
        return self.LEFT_PADDING_PX + self.RIGHT_PADDING_PX + digit_width * digits

    def sizeHint(self) -> QSize:
        return QSize(self.calculate_width(), 0)

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)

        palette = self.editor.palette()
        background_color = palette.color(palette.ColorRole.Base)
        painter.fillRect(event.rect(), background_color.darker(110))

        font_height = self.fontMetrics().height()
        font_width = self.width() - self.RIGHT_PADDING_PX
        top = self.editor.contentOffset().y()

        painter.setPen(palette.color(palette.ColorRole.PlaceholderText))
        for line_index, block in iterate_visible_blocks(self.editor):
            painter.drawText(
                0, top, font_width, font_height,
                Qt.AlignRight, str(line_index + 1),
            )
            top += self.editor.blockBoundingRect(block).height()

    @Slot(QRect, int)
    def update_with_editor(self, rect: QRect, dy: int) -> None:
        if dy:
            self.scroll(0, dy)
        else:
            self.update(0, rect.y(), self.width(), rect.height())

    @Slot()
    def update_width(self):
        width = self.calculate_width()
        self.setFixedWidth(width)


class CodeEditor(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.editor = QPlainTextEdit(self)
        self.editor.setFrameShape(QPlainTextEdit.Shape.NoFrame)
        self.editor.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)

        self.line_numbers = LineNumbers(self.editor)

        layout = QHBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.line_numbers)
        layout.addWidget(self.editor)

        self.editor.updateRequest.connect(self.line_numbers.update_with_editor)
        self.editor.blockCountChanged.connect(self.line_numbers.update_width)

        self.line_numbers.update_width()

    def setText(self, text: str):
        self.editor.setPlainText(text)
        return self

    def setReadOnly(self, value: bool = True):
        self.editor.setReadOnly(value)



class DiffEditor(QWidget):
    UPDATE_DELAY_MS = 300

    def __init__(self, parent=None):
        super().__init__(parent)

        self.old = CodeEditor()
        self.new = CodeEditor()
        self.old.setReadOnly(True)

        self._sync_scroll_bars()

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
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
            """\
def hello_world():
    # This is the original function
    print("Hello, world!")

# Unchanged line
""",
            """\
def hello_universe():
    # This function was modified
    print("Hello, beautiful universe!")

# Unchanged line
"""
        )


def main(argv: list[str] = sys.argv):
    signal.signal(signal.SIGINT, signal.SIG_DFL)  # handle CTRL-C

    app = QApplication(argv)
    if DARK_STYLE_SHEET:
        app.setStyleSheet(DARK_STYLE_SHEET)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
