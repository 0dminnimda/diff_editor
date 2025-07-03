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
from PySide6.QtGui import (
    QPainter,
    QColor,
    QPaintEvent,
    QSyntaxHighlighter,
    QTextCharFormat,
    QTextDocument,
    QFont,
)

from pygments import highlight
from pygments.lexers import PythonLexer
from pygments.token import Token


DIR = Path(__file__).parent
DARK_STYLE_SHEET_FILE = DIR/"dark_mode.qss"
# TODO: https://github.com/5yutan5/PyQtDarkTheme/blob/main/style/base.qss

if DARK_STYLE_SHEET_FILE.exists():
    DARK_STYLE_SHEET = DARK_STYLE_SHEET_FILE.read_text()
else:
    DARK_STYLE_SHEET = ""


class PygmentsHighlighter(QSyntaxHighlighter):
    def __init__(self, parent: QTextDocument, lexer):
        super().__init__(parent)
        self.lexer = lexer
        self.styles = self._chromodynamics_styles()

    def _default_styles(self):
        return {
            Token.Keyword         : self._create_format(QColor("#C586C0")),
            Token.Name.Function   : self._create_format(QColor("#DCDCAA")),
            Token.Name.Class      : self._create_format(QColor("#4EC9B0")),
            Token.String          : self._create_format(QColor("#CE9178")),
            Token.Comment         : self._create_format(QColor("#6A9955"), italic=True),
            Token.Operator        : self._create_format(QColor("#D4D4D4")),
            Token.Number          : self._create_format(QColor("#B5CEA8")),
            Token.Keyword.Constant: self._create_format(QColor("#569CD6")),
            Token.Name.Builtin    : self._create_format(QColor("#4EC9B0")),
            Token.Name.Decorator  : self._create_format(QColor("#DCDCAA")),
        }

    def _chromodynamics_styles(self):
        flow_kw_format  = self._create_format(QColor("#E8364F"))
        decl_kw_format  = self._create_format(QColor("#66D9EF"))
        const_format    = self._create_format(QColor("#9A79D7"))
        decl_ref_format = self._create_format(QColor("#A6E22E"))
        str_format      = self._create_format(QColor("#D3C970"))
        spec_id_format  = self._create_format(QColor("#C9C8B6"), bold=True)
        comment_format  = self._create_format(QColor("#33CC33"), bold=True)
        default_format  = self._create_format(QColor("#C6C6C6"))

        return {
            Token.Comment            : comment_format,
            Token.Keyword.Constant   : const_format,  # True, False, None
            Token.Keyword.Declaration: decl_kw_format,  # def, class
            Token.Keyword.Control    : flow_kw_format,  # if, for, while, return
            Token.Keyword            : flow_kw_format,  # Other keywords
            Token.Operator           : flow_kw_format,  # +, -, =, etc.
            Token.Number             : const_format,
            Token.String             : str_format,
            Token.Name.Function      : decl_ref_format,
            Token.Name.Class         : decl_ref_format,
            Token.Name.Decorator     : decl_ref_format,
            Token.Name.Builtin       : decl_kw_format,  # print, len, etc.
            Token.Name.Builtin.Pseudo: spec_id_format,  # self, cls
            Token.Name               : default_format,
            Token.Text               : default_format,
        }

    def _create_format(self, color: QColor, bold: bool = False, italic: bool = False) -> QTextCharFormat:
        fmt = QTextCharFormat()
        fmt.setForeground(color)
        if bold:
            fmt.setFontWeight(QFont.Weight.Bold)
        if italic:
            fmt.setFontItalic(True)
        return fmt

    def _find_best_style(self, token_type) -> QTextCharFormat:
        while token_type not in self.styles and token_type.parent:
            token_type = token_type.parent
        return self.styles.get(token_type) or QTextCharFormat()

    def highlightBlock(self, text: str) -> None:
        for index, token_type, value in self.lexer.get_tokens_unprocessed(text):
            self.setFormat(index, len(value), self._find_best_style(token_type))


def count_digits(x: int) -> int:
    return len(str(x)) if x > 0 else 1


def iterate_viewport_blocks(editor: QPlainTextEdit):
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
        super().__init__()
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
        block_top = self.editor.contentOffset().y()

        painter.setPen(palette.color(palette.ColorRole.PlaceholderText))
        for line_index, block in iterate_viewport_blocks(self.editor):
            if block_top > event.rect().bottom():
                break
            painter.drawText(
                0, block_top, font_width, font_height,
                Qt.AlignRight, str(line_index + 1),
            )
            block_top += self.editor.blockBoundingRect(block).height()

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

        self.highlighter = PygmentsHighlighter(self.editor.document(), PythonLexer())

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
@decorator
def hello_world():
    # This is the original function
    print("Hello, world!")
    a = 1 + 2 # A comment

# Unchanged line
class MyClass:
    pass
""",
            """\
@decorator
def hello_universe():
    # This function was modified
    print(f"Hello, beautiful {1+1} universe!")
    a = 1 + 2 # A comment

# Unchanged line
class MyClass:
    def __init__(self):
        pass
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


# TODO: allow to move the separator
# TODO: guess the language
