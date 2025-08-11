import sys
import difflib
from enum import Enum, auto

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout,
    QPlainTextEdit, QSplitter, QTextEdit  # ### ИЗМЕНЕНИЕ: Добавили QTextEdit
)
from PySide6.QtGui import QPainter, QFont, QColor, QTextFormat, QTextCursor
from PySide6.QtCore import Qt, QRect, QSize

# Используем тот же Enum
class DiffType(Enum):
    EQUAL = auto()
    INSERT = auto()
    DELETE = auto()
    REPLACE = auto()

# Уникальная строка-маркер для пустых строк, которые мы вставляем для выравнивания
SPACER_LINE_TEXT = ""

# 1. Виджет для отрисовки номеров строк
class LineNumberArea(QWidget):
    def __init__(self, editor, diff_viewer):
        super().__init__(editor)
        self.editor = editor
        self.diff_viewer = diff_viewer
        self.is_left_panel = (editor == diff_viewer.editor_new)

    def sizeHint(self):
        return QSize(self.editor.lineNumberAreaWidth(), 0)

    def paintEvent(self, event):
        self.editor.lineNumberAreaPaintEvent(event, self)

# 2. Основной редактируемый Diff Viewer
class EditableDiffViewer(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.editor_new = QPlainTextEdit()
        self.editor_old = QPlainTextEdit()

        self.editor_new.setReadOnly(False)
        self.editor_old.setReadOnly(True) 

        font = QFont("Consolas", 10)
        self.editor_new.setFont(font)
        self.editor_old.setFont(font)

        self.line_number_area_new = LineNumberArea(self.editor_new, self)
        self.line_number_area_old = LineNumberArea(self.editor_old, self)

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.line_number_area_new)
        layout.addWidget(self.editor_new)
        separator = QWidget()
        separator.setFixedWidth(2)
        separator.setStyleSheet("background-color: #444;")
        layout.addWidget(separator)
        layout.addWidget(self.line_number_area_old)
        layout.addWidget(self.editor_old)
        self.setLayout(layout)
        
        self.new_linenos = []
        self.old_linenos = []
        
        self._is_updating = False

        self.connect_signals()

        self.colors = {
            'background': QColor("#2b2b2b"),
            'text': QColor("#a9b7c6"),
            'lineno': QColor("#606366"),
            'lineno_bg': QColor("#313335"),
            'insert_bg': QColor("#2d4234"),
            'delete_bg': QColor("#5a343a"),
        }
        self.setup_editor_styles()

    def connect_signals(self):
        self.editor_new.verticalScrollBar().valueChanged.connect(self.editor_old.verticalScrollBar().setValue)
        self.editor_old.verticalScrollBar().valueChanged.connect(self.editor_new.verticalScrollBar().setValue)

        self.editor_new.updateRequest.connect(self.update_line_number_area)
        self.editor_old.updateRequest.connect(self.update_line_number_area)
        self.editor_new.blockCountChanged.connect(self.update_line_number_area_width)
        self.editor_old.blockCountChanged.connect(self.update_line_number_area_width)
        
        self.editor_new.textChanged.connect(self._update_diff)
        self.editor_old.textChanged.connect(self._update_diff)

    def setup_editor_styles(self):
        for editor in [self.editor_new, self.editor_old]:
            editor.setStyleSheet(f"""
                QPlainTextEdit {{
                    background-color: {self.colors['background'].name()};
                    color: {self.colors['text'].name()};
                    border: none;
                }}
            """)
            editor.lineNumberAreaWidth = lambda: 50
            editor.lineNumberAreaPaintEvent = lambda event, area: self.lineNumberAreaPaintEvent(event, area)

    def set_diff_text(self, new_text: str, old_text: str):
        self._is_updating = True
        self.editor_new.setPlainText(new_text)
        self.editor_old.setPlainText(old_text)
        self._is_updating = False
        self._update_diff()

    def _update_diff(self):
        if self._is_updating:
            return

        self._is_updating = True

        new_text_clean = self.editor_new.toPlainText()
        old_text_clean = self.editor_old.toPlainText()
        
        new_lines = new_text_clean.splitlines()
        old_lines = old_text_clean.splitlines()

        matcher = difflib.SequenceMatcher(None, old_lines, new_lines)

        new_padded_lines, old_padded_lines = [], []
        self.new_linenos, self.old_linenos = [], []
        new_selections, old_selections = [], []

        # ### ИЗМЕНЕНИЕ: Вспомогательная функция теперь использует QTextEdit.ExtraSelection ###
        def create_selection(color):
            selection = QTextEdit.ExtraSelection() 
            selection.format.setBackground(color)
            selection.format.setProperty(QTextFormat.FullWidthSelection, True)
            return selection

        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == 'equal':
                for i in range(i2 - i1):
                    new_padded_lines.append(new_lines[j1 + i])
                    old_padded_lines.append(old_lines[i1 + i])
                    self.new_linenos.append(j1 + i + 1)
                    self.old_linenos.append(i1 + i + 1)
            else:
                num_new, num_old = j2 - j1, i2 - i1
                
                # Применяем подсветку к будущим блокам
                for i in range(num_new):
                    selection = create_selection(self.colors['insert_bg'])
                    selection.cursor = QTextCursor(self.editor_new.document().findBlockByNumber(len(new_padded_lines) + i))
                    new_selections.append(selection)

                for i in range(num_old):
                    selection = create_selection(self.colors['delete_bg'])
                    selection.cursor = QTextCursor(self.editor_old.document().findBlockByNumber(len(old_padded_lines) + i))
                    old_selections.append(selection)
                
                for i in range(max(num_new, num_old)):
                    is_new_line_available = i < num_new
                    is_old_line_available = i < num_old

                    new_padded_lines.append(new_lines[j1 + i] if is_new_line_available else SPACER_LINE_TEXT)
                    old_padded_lines.append(old_lines[i1 + i] if is_old_line_available else SPACER_LINE_TEXT)

                    self.new_linenos.append(j1 + i + 1 if is_new_line_available else None)
                    self.old_linenos.append(i1 + i + 1 if is_old_line_available else None)

        cursor_new_pos = self.editor_new.textCursor().position()
        cursor_old_pos = self.editor_old.textCursor().position()

        self.editor_new.setPlainText("\n".join(new_padded_lines))
        self.editor_old.setPlainText("\n".join(old_padded_lines))
        
        self.editor_new.setExtraSelections(new_selections)
        self.editor_old.setExtraSelections(old_selections)

        cursor_new = self.editor_new.textCursor()
        cursor_new.setPosition(cursor_new_pos)
        self.editor_new.setTextCursor(cursor_new)

        cursor_old = self.editor_old.textCursor()
        cursor_old.setPosition(cursor_old_pos)
        self.editor_old.setTextCursor(cursor_old)

        self.update_line_number_area_width()
        self._is_updating = False

    def update_line_number_area_width(self, newBlockCount=0):
        width = self.fontMetrics().horizontalAdvance('9' * 4 + ' ')
        self.editor_new.setViewportMargins(width, 0, 0, 0)
        self.editor_old.setViewportMargins(width, 0, 0, 0)

    def update_line_number_area(self, rect, dy):
        if dy:
            self.line_number_area_new.scroll(0, dy)
            self.line_number_area_old.scroll(0, dy)
        else:
            self.line_number_area_new.update(0, rect.y(), self.line_number_area_new.width(), rect.height())
            self.line_number_area_old.update(0, rect.y(), self.line_number_area_old.width(), rect.height())

    def lineNumberAreaPaintEvent(self, event, area):
        painter = QPainter(area)
        painter.fillRect(event.rect(), self.colors['lineno_bg'])

        editor = area.editor
        is_left = area.is_left_panel
        linenos = self.new_linenos if is_left else self.old_linenos

        block = editor.firstVisibleBlock()
        block_number = block.blockNumber()
        top = int(editor.blockBoundingGeometry(block).translated(editor.contentOffset()).top())
        bottom = top + int(editor.blockBoundingRect(block).height())

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                if block_number < len(linenos) and linenos[block_number] is not None:
                    number = str(linenos[block_number])
                    painter.setPen(self.colors['lineno'])
                    painter.drawText(0, top, area.width() - 5, editor.fontMetrics().height(),
                                     Qt.AlignRight, number)

            block = block.next()
            top = bottom
            bottom = top + int(editor.blockBoundingRect(block).height())
            block_number += 1


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Editable Side-by-Side Diff Viewer")
        self.setGeometry(100, 100, 1400, 800)
        
        self.diff_viewer = EditableDiffViewer()
        self.setCentralWidget(self.diff_viewer)

        old_text = """import os

def hello_world():
    # This is a great function
    print("Hello, world!")
    return True

# Program entry point
if __name__ == "__main__":
    hello_world()
"""
        new_text = """import sys
import os

def hello_world(name="world"):
    # This is a wonderful function
    print(f"Hello, {name}!")
    return True

def main():
    # Program entry point
    hello_world("PySide6")

if __name__ == "__main__":
    main()
"""
        self.diff_viewer.set_diff_text(new_text, old_text)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
