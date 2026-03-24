"""
Central PDF page viewer with navigation and zoom controls.
"""
from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap, QWheelEvent
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

_BTN_STYLE = (
    "QPushButton {"
    "  color: #ffffff;"
    "  background: #444444;"
    "  border: 1px solid #666666;"
    "  border-radius: 3px;"
    "  padding: 4px 10px;"
    "}"
    "QPushButton:hover { background: #555555; }"
    "QPushButton:disabled { color: #777777; background: #333333; }"
)


class PDFViewer(QWidget):
    """Displays a single PDF page with zoom / navigate controls."""

    page_changed = pyqtSignal(int)  # user requested a different page index

    _ZOOM_STEP = 1.25
    _ZOOM_MIN = 0.10
    _ZOOM_MAX = 5.00

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._current_page = 0
        self._total_pages = 0
        self._original_pixmap: QPixmap | None = None
        self._zoom = 1.0
        self._setup_ui()

    # ------------------------------------------------------------------
    # UI setup
    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Nav bar ──────────────────────────────────────────────────
        nav = QWidget()
        nav.setStyleSheet("background:#2b2b2b;")
        nav_layout = QHBoxLayout(nav)
        nav_layout.setContentsMargins(8, 4, 8, 4)
        nav_layout.setSpacing(6)

        self._prev_btn = QPushButton("◀  Prev")
        self._prev_btn.setStyleSheet(_BTN_STYLE)
        self._prev_btn.clicked.connect(self._go_prev)

        self._page_label = QLabel("—  /  —")
        self._page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._page_label.setStyleSheet("color:#ffffff; min-width:110px;")

        self._next_btn = QPushButton("Next  ▶")
        self._next_btn.setStyleSheet(_BTN_STYLE)
        self._next_btn.clicked.connect(self._go_next)

        # Zoom
        zoom_lbl = QLabel("Zoom:")
        zoom_lbl.setStyleSheet("color:#cccccc; margin-left:20px;")

        self._zoom_out_btn = QPushButton("−")
        self._zoom_out_btn.setFixedWidth(30)
        self._zoom_out_btn.setStyleSheet(_BTN_STYLE)
        self._zoom_out_btn.clicked.connect(self.zoom_out)

        self._zoom_label = QLabel("100 %")
        self._zoom_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._zoom_label.setStyleSheet("color:#ffffff; min-width:55px;")

        self._zoom_in_btn = QPushButton("+")
        self._zoom_in_btn.setFixedWidth(30)
        self._zoom_in_btn.setStyleSheet(_BTN_STYLE)
        self._zoom_in_btn.clicked.connect(self.zoom_in)

        self._fit_btn = QPushButton("Fit")
        self._fit_btn.setStyleSheet(_BTN_STYLE)
        self._fit_btn.clicked.connect(self.zoom_reset)

        nav_layout.addWidget(self._prev_btn)
        nav_layout.addWidget(self._page_label)
        nav_layout.addWidget(self._next_btn)
        nav_layout.addStretch()
        nav_layout.addWidget(zoom_lbl)
        nav_layout.addWidget(self._zoom_out_btn)
        nav_layout.addWidget(self._zoom_label)
        nav_layout.addWidget(self._zoom_in_btn)
        nav_layout.addWidget(self._fit_btn)

        root.addWidget(nav)

        # ── Scroll area ───────────────────────────────────────────────
        self._scroll = QScrollArea()
        self._scroll.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._scroll.setStyleSheet("background:#505050; border:none;")
        self._scroll.setWidgetResizable(False)

        self._image_label = QLabel()
        self._image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._image_label.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed
        )
        self._scroll.setWidget(self._image_label)

        root.addWidget(self._scroll)

        self._refresh_nav()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def display_page(self, pixmap: QPixmap, page_index: int, total: int) -> None:
        self._original_pixmap = pixmap
        self._current_page = page_index
        self._total_pages = total
        self._apply_zoom()
        self._page_label.setText(f"Page  {page_index + 1}  /  {total}")
        self._refresh_nav()

    def clear(self) -> None:
        self._original_pixmap = None
        self._current_page = 0
        self._total_pages = 0
        self._image_label.clear()
        self._image_label.resize(0, 0)
        self._page_label.setText("—  /  —")
        self._refresh_nav()

    def zoom_in(self) -> None:
        self._zoom = min(self._zoom * self._ZOOM_STEP, self._ZOOM_MAX)
        self._apply_zoom()

    def zoom_out(self) -> None:
        self._zoom = max(self._zoom / self._ZOOM_STEP, self._ZOOM_MIN)
        self._apply_zoom()

    def zoom_reset(self) -> None:
        self._zoom = 1.0
        self._apply_zoom()

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _apply_zoom(self) -> None:
        if not self._original_pixmap:
            return
        w = int(self._original_pixmap.width() * self._zoom)
        h = int(self._original_pixmap.height() * self._zoom)
        scaled = self._original_pixmap.scaled(
            w, h,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self._image_label.setPixmap(scaled)
        self._image_label.resize(scaled.size())
        self._zoom_label.setText(f"{int(self._zoom * 100)} %")

    def _go_prev(self) -> None:
        if self._current_page > 0:
            self.page_changed.emit(self._current_page - 1)

    def _go_next(self) -> None:
        if self._current_page < self._total_pages - 1:
            self.page_changed.emit(self._current_page + 1)

    def _refresh_nav(self) -> None:
        self._prev_btn.setEnabled(self._current_page > 0)
        self._next_btn.setEnabled(self._current_page < self._total_pages - 1)

    # Ctrl+Scroll → zoom
    def wheelEvent(self, event: QWheelEvent) -> None:  # noqa: N802
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            if event.angleDelta().y() > 0:
                self.zoom_in()
            else:
                self.zoom_out()
            event.accept()
        else:
            super().wheelEvent(event)
