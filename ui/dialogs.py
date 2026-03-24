"""
Dialogs used by the main window.
"""
from __future__ import annotations

import fitz
from PyQt6.QtCore import QObject, QSize, Qt, QThread, pyqtSignal
from PyQt6.QtGui import QImage, QIcon, QPixmap
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


# ──────────────────────────────────────────────────────────────────────────────
# Background thumbnail loader for the dialog
# ──────────────────────────────────────────────────────────────────────────────

class _ThumbWorker(QObject):
    thumb_ready = pyqtSignal(int, QPixmap)
    finished = pyqtSignal()

    def __init__(self, filepath: str, zoom: float = 0.22) -> None:
        super().__init__()
        self._filepath = filepath
        self._zoom = zoom
        self._running = True

    def run(self) -> None:
        try:
            doc = fitz.open(self._filepath)
            mat = fitz.Matrix(self._zoom, self._zoom)
            for i in range(len(doc)):
                if not self._running:
                    break
                pix = doc[i].get_pixmap(matrix=mat, alpha=False)
                img = QImage(
                    pix.samples, pix.width, pix.height,
                    pix.stride, QImage.Format.Format_RGB888,
                )
                self.thumb_ready.emit(i, QPixmap.fromImage(img))
            doc.close()
        except Exception as e:
            print(f"[ThumbWorker] {e}")
        finally:
            self.finished.emit()

    def stop(self) -> None:
        self._running = False


# ──────────────────────────────────────────────────────────────────────────────
# Page-selection dialog
# ──────────────────────────────────────────────────────────────────────────────

class PageSelectDialog(QDialog):
    """
    Shows all pages of a PDF as thumbnails; the user picks which ones to insert.
    """

    def __init__(self, filepath: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._filepath = filepath
        self._thread: QThread | None = None
        self._worker: _ThumbWorker | None = None
        self._setup_ui()
        self._load_pages()
        name = filepath.replace("\\", "/").split("/")[-1]
        self.setWindowTitle(f"Select Pages — {name}")
        self.resize(560, 640)

    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        hint = QLabel(
            "選擇要插入的頁面（Ctrl+點擊 多選 | Ctrl+A 全選）："
        )
        hint.setWordWrap(True)
        layout.addWidget(hint)

        self._list = QListWidget()
        self._list.setViewMode(QListWidget.ViewMode.IconMode)
        self._list.setIconSize(QSize(110, 145))
        self._list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self._list.setResizeMode(QListWidget.ResizeMode.Adjust)
        self._list.setSpacing(8)
        self._list.setStyleSheet(
            "QListWidget { background:#3a3a3a; border:none; }"
            "QListWidget::item { color:#cccccc; border-radius:3px; padding:4px; }"
            "QListWidget::item:selected { background:#0078d4; }"
        )
        layout.addWidget(self._list)

        btn_row = QHBoxLayout()
        sel_all = QPushButton("全選")
        sel_all.clicked.connect(self._list.selectAll)
        btn_row.addWidget(sel_all)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def _load_pages(self) -> None:
        try:
            doc = fitz.open(self._filepath)
            count = len(doc)
            doc.close()
        except Exception as e:
            print(f"[PageSelectDialog] open error: {e}")
            return

        for i in range(count):
            item = QListWidgetItem(f"第 {i + 1} 頁")
            item.setTextAlignment(
                Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom
            )
            self._list.addItem(item)

        self._thread = QThread()
        self._worker = _ThumbWorker(self._filepath)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.thumb_ready.connect(self._on_thumb)
        self._worker.finished.connect(self._thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.start()

    def _on_thumb(self, index: int, pixmap: QPixmap) -> None:
        if index < self._list.count():
            self._list.item(index).setIcon(QIcon(pixmap))

    def _stop_worker(self) -> None:
        if self._worker:
            self._worker.stop()
        if self._thread and self._thread.isRunning():
            self._thread.quit()
            self._thread.wait(1000)

    # ------------------------------------------------------------------

    def get_selected_pages(self) -> list[int]:
        return sorted(self._list.row(item) for item in self._list.selectedItems())

    def reject(self) -> None:
        self._stop_worker()
        super().reject()

    def closeEvent(self, event) -> None:  # noqa: N802
        self._stop_worker()
        super().closeEvent(event)
