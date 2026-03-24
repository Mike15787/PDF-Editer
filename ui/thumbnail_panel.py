"""
Left panel: scrollable list of page thumbnails with drag-drop reordering.
"""
from __future__ import annotations

from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtGui import QColor, QIcon, QPixmap
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)


class _ReorderableList(QListWidget):
    """QListWidget that emits (from_row, to_row) after a successful drag-drop."""

    page_moved = pyqtSignal(int, int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._drag_src: int = -1
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setIconSize(QSize(130, 170))
        self.setSpacing(4)
        self.setUniformItemSizes(True)

    def startDrag(self, supported_actions):  # noqa: N802
        self._drag_src = self.currentRow()
        super().startDrag(supported_actions)

    def dropEvent(self, event):  # noqa: N802
        super().dropEvent(event)
        dest = self.currentRow()
        src = self._drag_src
        self._drag_src = -1
        if src != -1 and src != dest:
            self.page_moved.emit(src, dest)


class ThumbnailPanel(QWidget):
    """Left-side panel showing page thumbnails."""

    page_selected = pyqtSignal(int)   # user clicked a thumbnail
    page_moved = pyqtSignal(int, int) # drag-drop reorder (from, to)

    _PLACEHOLDER_COLOR = "#606060"

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._updating = False
        self._setup_ui()

    # ------------------------------------------------------------------
    # UI setup
    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QLabel("Pages")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setStyleSheet(
            "background:#2b2b2b; color:#ffffff; padding:5px; font-weight:bold;"
        )
        layout.addWidget(header)

        self.list = _ReorderableList()
        self.list.page_moved.connect(self.page_moved)
        self.list.currentRowChanged.connect(self._on_row_changed)
        self.list.setStyleSheet(
            """
            QListWidget {
                background: #3c3c3c;
                border: none;
            }
            QListWidget::item {
                color: #cccccc;
                border: 1px solid #555555;
                margin: 3px 4px;
                border-radius: 3px;
                padding: 3px;
            }
            QListWidget::item:selected {
                background: #0078d4;
                border: 1px solid #005a9e;
                color: #ffffff;
            }
            QListWidget::item:hover:!selected {
                background: #4d4d4d;
            }
            """
        )
        layout.addWidget(self.list)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def clear(self) -> None:
        self.list.clear()

    def set_page_count(self, count: int) -> None:
        """Pre-populate items with grey placeholder icons."""
        self.list.clear()
        placeholder = self._make_placeholder()
        icon = QIcon(placeholder)
        for i in range(count):
            item = QListWidgetItem(icon, f"Page {i + 1}")
            item.setTextAlignment(
                Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom
            )
            self.list.addItem(item)

    def update_thumbnail(self, page_index: int, pixmap: QPixmap) -> None:
        if page_index < self.list.count():
            self.list.item(page_index).setIcon(QIcon(pixmap))

    def select_page(self, index: int) -> None:
        self._updating = True
        self.list.setCurrentRow(index)
        item = self.list.item(index)
        if item:
            self.list.scrollToItem(item, QAbstractItemView.ScrollHint.EnsureVisible)
        self._updating = False

    def get_selected_indices(self) -> list[int]:
        return sorted(self.list.row(item) for item in self.list.selectedItems())

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _on_row_changed(self, row: int) -> None:
        if not self._updating and row >= 0:
            self.page_selected.emit(row)

    @staticmethod
    def _make_placeholder(w: int = 130, h: int = 170) -> QPixmap:
        pix = QPixmap(w, h)
        pix.fill(QColor(ThumbnailPanel._PLACEHOLDER_COLOR))
        return pix
