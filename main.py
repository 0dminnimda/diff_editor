import sys
import signal
from pathlib import Path
import fast_diff_match_patch
from difflib import SequenceMatcher

from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QMainWindow,
    QPlainTextEdit,
    QHBoxLayout,
    QTextEdit,
    QSplitter,
)
from PySide6.QtCore import (
    Qt,
    QTimer,
    QRect,
    QSize,
    Slot,
    Signal,
)
from PySide6.QtGui import (
    QPainter,
    QColor,
    QPaintEvent,
    QSyntaxHighlighter,
    QTextCharFormat,
    QTextDocument,
    QFont,
    QTextCursor,
    QTextFormat,
)

from pygments import highlight
from pygments.lexers import PythonLexer, TextLexer
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
        # self.styles = self._default_styles()
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


class CollapsiblePlainTextEdit(QPlainTextEdit):
    placeholderClicked = Signal(int)

    def mousePressEvent(self, event):
        cursor = self.cursorForPosition(event.position().toPoint())
        block = cursor.block()
        state = block.userState()
        if state > 0:
            self.placeholderClicked.emit(state - 1)
        super().mousePressEvent(event)

    def selection_includes_placeholder(self):
        cursor = self.textCursor()
        if not cursor.hasSelection():
            return False
        start = cursor.selectionStart()
        end = cursor.selectionEnd()
        block = self.document().findBlock(start)
        while block.isValid() and block.position() < end:
            if block.userState() > 0:
                return True
            block = block.next()
        return False

    def keyPressEvent(self, event):
        cursor = self.textCursor()
        if cursor.hasSelection():
            if self.selection_includes_placeholder():
                # Allow navigation and copying when selection includes placeholders
                if event.modifiers() & Qt.ControlModifier and event.key() == Qt.Key_C:
                    super().keyPressEvent(event)
                elif event.key() in (Qt.Key_Left, Qt.Key_Right, Qt.Key_Up, Qt.Key_Down,
                                   Qt.Key_Home, Qt.Key_End, Qt.Key_PageUp, Qt.Key_PageDown):
                    super().keyPressEvent(event)
                # Ignore all other keys (e.g., Delete, Backspace, typing)
            else:
                super().keyPressEvent(event)
        else:
            block = cursor.block()
            if block.userState() > 0:
                # Allow only navigation keys on placeholder lines
                if event.key() in (Qt.Key_Left, Qt.Key_Right, Qt.Key_Up, Qt.Key_Down,
                                 Qt.Key_Home, Qt.Key_End, Qt.Key_PageUp, Qt.Key_PageDown):
                    super().keyPressEvent(event)
                # Ignore all other keys (e.g., typing, Backspace, Delete)
            else:
                super().keyPressEvent(event)

    def insertFromMimeData(self, source):
        cursor = self.textCursor()
        if cursor.hasSelection():
            if self.selection_includes_placeholder():
                return  # Prevent pasting over a selection with placeholders
        else:
            block = cursor.block()
            if block.userState() > 0:
                return  # Prevent pasting on a placeholder line
        super().insertFromMimeData(source)


class CodeEditor(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.editor = CollapsiblePlainTextEdit(self)
        self.editor.setFrameShape(QPlainTextEdit.Shape.NoFrame)
        self.editor.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)

        self.line_numbers = LineNumbers(self.editor)

        self.highlighter = None

        layout = QHBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.line_numbers)
        layout.addWidget(self.editor)

        self.editor.updateRequest.connect(self.line_numbers.update_with_editor)
        self.editor.blockCountChanged.connect(self.line_numbers.update_width)

        self.line_numbers.update_width()

    def set_lexer(self, lexer):
        """Creates or replaces the syntax highlighter."""
        if self.highlighter:
            # Clean up the old one to be safe
            self.highlighter.setDocument(None)
            self.highlighter.setParent(None)

        self.highlighter = PygmentsHighlighter(self.editor.document(), lexer)
        # Re-highlighting is necessary if text is already present
        self.highlighter.rehighlight()

    def setText(self, text: str):
        self.editor.setPlainText(text)
        return self

    def setReadOnly(self, value: bool = True):
        self.editor.setReadOnly(value)

    def apply_highlights(self, highlights: list[QTextEdit.ExtraSelection]):
        self.editor.setExtraSelections(highlights)


class DiffEditor(QWidget):
    UPDATE_DELAY_MS = 300
    COLLAPSE_THRESHOLD = 5

    ADD_COLOR = QColor(20, 200, 20, 100)
    DEL_COLOR = QColor(200, 20, 20, 100)

    PLACEHOLDER_COLOR = QColor(60, 60, 60)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.old = CodeEditor()
        self.new = CodeEditor()
        self.old.setReadOnly(True)

        self._sync_scroll_bars()

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self.old)
        splitter.addWidget(self.new)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(splitter)

        self._update_diff_when(self.new.editor.textChanged)
        self.old.editor.placeholderClicked.connect(self.expand_section)
        self.new.editor.placeholderClicked.connect(self.expand_section)
        self.set_diff_text("", "", TextLexer())

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

    def set_diff_text(self, old: str, new: str, lexer):
        self.old.set_lexer(lexer)
        self.new.set_lexer(lexer)

        self.original_old = old.splitlines(keepends=True)
        self.original_new = new.splitlines(keepends=True)
        matcher = SequenceMatcher(None, self.original_old, self.original_new, autojunk=False)

        self.collapsed_sections = []  # List of original lines for each collapsed section
        placeholders_to_set = {self.old.editor: [], self.new.editor: []}

        displayed_old_parts = []
        displayed_new_parts = []

        old_line_num = 0
        new_line_num = 0

        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == 'equal' and (i2 - i1) > self.COLLAPSE_THRESHOLD:
                placeholder = f"[{i2 - i1} lines hidden, click to expand]\n"
                collapse_index = len(self.collapsed_sections)
                self.collapsed_sections.append(self.original_old[i1:i2])

                displayed_old_parts.append(placeholder)
                displayed_new_parts.append(placeholder)

                placeholders_to_set[self.old.editor].append((old_line_num, collapse_index))
                placeholders_to_set[self.new.editor].append((new_line_num, collapse_index))

                old_line_num += 1
                new_line_num += 1
            else:
                displayed_old_parts.extend(self.original_old[i1:i2])
                displayed_new_parts.extend(self.original_new[j1:j2])
                old_line_num += (i2 - i1)
                new_line_num += (j2 - j1)

        self.old.setText(''.join(displayed_old_parts))
        self.new.setText(''.join(displayed_new_parts))

        for editor, placeholders in placeholders_to_set.items():
            doc = editor.document()
            for line_num, collapse_index in placeholders:
                block = doc.findBlockByLineNumber(line_num)
                if block.isValid():
                    block.setUserState(collapse_index + 1)

        self.update_diff()
        return self

    def _create_placeholder_text_format(self) -> QTextCharFormat:
        fmt = QTextCharFormat()
        fmt.setForeground(QColor("#888888"))
        fmt.setFontItalic(True)
        return fmt

    def _get_placeholder_highlights(self, editor: CodeEditor) -> list[QTextEdit.ExtraSelection]:
        selections = []
        placeholder_format = QTextCharFormat()
        placeholder_format.setBackground(self.PLACEHOLDER_COLOR)
        placeholder_format.setProperty(QTextFormat.FullWidthSelection, True)

        # Style the text itself to look different
        text_format = self._create_placeholder_text_format()

        block = editor.editor.document().firstBlock()
        while block.isValid():
            if block.userState() > 0:
                # Apply special background
                selection = QTextEdit.ExtraSelection()
                selection.format = placeholder_format
                selection.cursor = QTextCursor(block)
                selections.append(selection)

                # Apply special text format
                text_selection = QTextEdit.ExtraSelection()
                text_selection.format = text_format
                cursor = QTextCursor(block)
                cursor.select(QTextCursor.SelectionType.LineUnderCursor)
                text_selection.cursor = cursor
                selections.append(text_selection)

            block = block.next()
        return selections

    def _one_diff_highlight(self, length: int, color, cursor):
        selection = QTextEdit.ExtraSelection()
        selection.format.setBackground(color)
        selection.format.setProperty(QTextFormat.FullWidthSelection, True)
        selection.cursor = cursor
        selection.cursor.setPosition(cursor.position())
        selection.cursor.movePosition(QTextCursor.NextCharacter, QTextCursor.KeepAnchor, length)
        cursor.movePosition(QTextCursor.NextCharacter, QTextCursor.MoveAnchor, length)
        return selection

    @Slot()
    def update_diff(self):
        old_text = self.old.editor.toPlainText()
        new_text = self.new.editor.toPlainText()

        opcodes = fast_diff_match_patch.diff(old_text, new_text, timelimit=0.1, checklines=True, counts_only=True)

        old_highlights = []
        new_highlights = []

        old_cursor = self.old.editor.textCursor()
        old_cursor.movePosition(QTextCursor.MoveOperation.Start)

        new_cursor = self.new.editor.textCursor()
        new_cursor.movePosition(QTextCursor.MoveOperation.Start)

        i = 0
        while i < len(opcodes):
            op, length = opcodes[i]

            is_modification = op == '-' and i + 1 < len(opcodes) and opcodes[i+1][0] == '+'
            if is_modification:
                old_highlights.append(self._one_diff_highlight(opcodes[i  ][1], self.DEL_COLOR, old_cursor))
                new_highlights.append(self._one_diff_highlight(opcodes[i+1][1], self.ADD_COLOR, new_cursor))
                i += 2
                continue

            if op == '+':
                new_highlights.append(self._one_diff_highlight(length, self.ADD_COLOR, new_cursor))
            elif op == '-':
                old_highlights.append(self._one_diff_highlight(length, self.DEL_COLOR, old_cursor))
            elif op == '=':
                old_cursor.movePosition(QTextCursor.NextCharacter, QTextCursor.MoveAnchor, length)
                new_cursor.movePosition(QTextCursor.NextCharacter, QTextCursor.MoveAnchor, length)
            i += 1

        # Get placeholder highlights and combine them with diff highlights
        old_placeholder_highlights = self._get_placeholder_highlights(self.old)
        new_placeholder_highlights = self._get_placeholder_highlights(self.new)

        self.old.apply_highlights(old_highlights + old_placeholder_highlights)
        self.new.apply_highlights(new_highlights + new_placeholder_highlights)

    @Slot(int)
    def expand_section(self, index):
        if 0 <= index < len(self.collapsed_sections):
            self._expand_section(index)

    def _expand_section(self, index):
        original_lines = self.collapsed_sections[index]
        text_to_insert = "".join(original_lines)

        for editor in [self.old.editor, self.new.editor]:
            doc = editor.document()
            block = doc.firstBlock()
            while block.isValid():
                if block.userState() == index + 1:
                    cursor = QTextCursor(block)
                    cursor.beginEditBlock()

                    # Select entire block including newline character
                    cursor.movePosition(QTextCursor.StartOfBlock)
                    cursor.movePosition(QTextCursor.EndOfBlock, QTextCursor.KeepAnchor)
                    cursor.movePosition(QTextCursor.NextCharacter, QTextCursor.KeepAnchor)  # Include newline

                    # Replace with original content
                    cursor.removeSelectedText()
                    cursor.insertText(text_to_insert)
                    cursor.endEditBlock()
                    break
                block = block.next()

        # Remove the expanded section and update remaining userStates
        del self.collapsed_sections[index]
        for editor in [self.old.editor, self.new.editor]:
            doc = editor.document()
            block = doc.firstBlock()
            while block.isValid():
                state = block.userState()
                if state > index + 1:
                    block.setUserState(state - 1)
                block = block.next()
        self.update_diff()



# prefix = "'''\n" + "asdfhpklaspdlkfjplsadkfjsaplj\n"*15 + "'''\n"
# suffix = "'''\n" + "pllppppppppllppplpppppp\n"*31 + "'''\n"

prefix = "a = 25\n"*15 + "\n"
suffix = "\n" + "b = 91\n"*31

OLD_TEXT = prefix + """\
@decorator
def hello_world():
    # This is the original function
    print("Hello, world!")
    a = 1 + 2 # A comment

# Unchanged line
class MyClass:
    pass
""" + suffix

NEW_TEXT = prefix + """\
@decorator
def hello_universe():
    # This function was modified
    print(f"Hello, beautiful {1+1} universe!")
    a = 1 + 2 # A comment

# Unchanged line
class MyClass:
    def __init__(self):
        pass
""" + suffix


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Diff Editor")
        self.resize(800, 600)

        diff_editor = DiffEditor(self)
        self.setCentralWidget(diff_editor)
        diff_editor.set_diff_text(OLD_TEXT, NEW_TEXT, PythonLexer())


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


# TODO: guess the language
# TODO: add the spacers
# TODO: make calculating diff not blocking for gui
# TODO: when collapsing still show some context around collapsed lines
