"""
Main application window.
"""
from __future__ import annotations

import os
import subprocess

from PyQt6.QtCore import QObject, Qt, QThread, pyqtSignal
from PyQt6.QtGui import QAction, QImage, QKeySequence, QPixmap
from PyQt6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QStatusBar,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from core.pdf_engine import PDFEngine
from ui.pdf_viewer import PDFViewer
from ui.thumbnail_panel import ThumbnailPanel


# ──────────────────────────────────────────────────────────────────────────────
# Background thumbnail loading
# ──────────────────────────────────────────────────────────────────────────────

class _ThumbnailWorker(QObject):
    thumbnail_ready = pyqtSignal(int, QPixmap)
    finished = pyqtSignal()

    def __init__(self, engine: PDFEngine, zoom: float = 0.20) -> None:
        super().__init__()
        self._engine = engine
        self._zoom = zoom
        self._running = True

    def run(self) -> None:
        for i in range(self._engine.page_count()):
            if not self._running:
                break
            pix = self._engine.render_page_pixmap(i, self._zoom)
            if pix:
                img = QImage(
                    pix.samples, pix.width, pix.height,
                    pix.stride, QImage.Format.Format_RGB888,
                )
                self.thumbnail_ready.emit(i, QPixmap.fromImage(img))
        self.finished.emit()

    def stop(self) -> None:
        self._running = False


# ──────────────────────────────────────────────────────────────────────────────
# Main window
# ──────────────────────────────────────────────────────────────────────────────

class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self._engine = PDFEngine()
        self._current_page = 0
        self._thumb_thread: QThread | None = None
        self._thumb_worker: _ThumbnailWorker | None = None

        self._build_ui()
        self._build_menu()
        self._build_toolbar()

        self.setWindowTitle("PDF Editor")
        self.resize(1280, 820)

    # ──────────────────────────────────────────────────────────────────
    # UI construction
    # ──────────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)

        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left: thumbnail panel
        self._thumb_panel = ThumbnailPanel()
        self._thumb_panel.page_selected.connect(self._on_thumb_selected)
        self._thumb_panel.page_moved.connect(self._on_page_moved)
        self._thumb_panel.setMinimumWidth(160)
        self._thumb_panel.setMaximumWidth(300)

        # Right: PDF viewer
        self._viewer = PDFViewer()
        self._viewer.page_changed.connect(self._on_viewer_page_changed)

        self._splitter.addWidget(self._thumb_panel)
        self._splitter.addWidget(self._viewer)
        self._splitter.setStretchFactor(0, 0)
        self._splitter.setStretchFactor(1, 1)
        self._splitter.setSizes([210, 1070])

        layout.addWidget(self._splitter)

        # Status bar
        self._status = QStatusBar()
        self.setStatusBar(self._status)
        self._status_lbl = QLabel("尚未開啟 PDF")
        self._status.addWidget(self._status_lbl)

    def _build_menu(self) -> None:
        mb = self.menuBar()

        # ── File ──────────────────────────────────────────────────────
        fm = mb.addMenu("檔案(&F)")

        self._add_action(fm, "開啟 PDF…", self._act_open,
                         shortcut=QKeySequence.StandardKey.Open)
        fm.addSeparator()
        self._add_action(fm, "儲存", self._act_save,
                         shortcut=QKeySequence.StandardKey.Save)
        self._add_action(fm, "另存新檔…", self._act_save_as,
                         shortcut=QKeySequence("Ctrl+Shift+S"))
        fm.addSeparator()
        self._add_action(fm, "以 10 頁為單位分割…", self._act_split)
        fm.addSeparator()
        self._add_action(fm, "關閉 PDF", self._act_close_pdf)

        # ── Page ──────────────────────────────────────────────────────
        pm = mb.addMenu("頁面(&P)")

        self._add_action(pm, "從其他 PDF 插入頁面…", self._act_add_pages)
        self._add_action(pm, "合併 PDF（附加到末尾）…", self._act_merge)
        pm.addSeparator()
        self._add_action(pm, "刪除選取頁面", self._act_delete,
                         shortcut=QKeySequence.StandardKey.Delete)
        pm.addSeparator()
        self._add_action(pm, "順時針旋轉 90°", lambda: self._act_rotate(90))
        self._add_action(pm, "逆時針旋轉 90°", lambda: self._act_rotate(-90))
        self._add_action(pm, "旋轉 180°", lambda: self._act_rotate(180))

        # ── View ──────────────────────────────────────────────────────
        vm = mb.addMenu("檢視(&V)")
        self._add_action(vm, "放大", self._viewer.zoom_in,
                         shortcut=QKeySequence("Ctrl+="))
        self._add_action(vm, "縮小", self._viewer.zoom_out,
                         shortcut=QKeySequence("Ctrl+-"))
        self._add_action(vm, "重置縮放", self._viewer.zoom_reset,
                         shortcut=QKeySequence("Ctrl+0"))

    def _build_toolbar(self) -> None:
        tb = QToolBar("主工具列")
        tb.setMovable(False)
        tb.setStyleSheet(
            "QToolBar { background:#2b2b2b; border-bottom:1px solid #444; spacing:4px; padding:2px; }"
            "QToolButton { color:#ffffff; background:#3c3c3c; border:1px solid #555;"
            "  border-radius:3px; padding:4px 8px; }"
            "QToolButton:hover { background:#505050; }"
            "QToolButton:pressed { background:#0078d4; }"
        )
        self.addToolBar(tb)

        def add(label: str, slot, tip: str = "") -> None:
            act = QAction(label, self)
            act.setToolTip(tip or label)
            act.triggered.connect(slot)
            tb.addAction(act)

        add("📂 開啟", self._act_open, "開啟 PDF 檔案")
        add("💾 儲存", self._act_save, "儲存目前 PDF")
        tb.addSeparator()
        add("➕ 插入頁面", self._act_add_pages, "從其他 PDF 插入指定頁面")
        add("🔗 合併 PDF", self._act_merge, "附加另一個 PDF 到末尾")
        tb.addSeparator()
        add("🗑 刪除頁面", self._act_delete, "刪除選取的頁面")
        tb.addSeparator()
        add("↻ 順轉", lambda: self._act_rotate(90), "順時針旋轉 90°")
        add("↺ 逆轉", lambda: self._act_rotate(-90), "逆時針旋轉 90°")
        add("⟳ 180°", lambda: self._act_rotate(180), "旋轉 180°")
        tb.addSeparator()
        add("✂ 每10頁分割", self._act_split, "以 10 頁為單位分割 PDF")

    # ──────────────────────────────────────────────────────────────────
    # Helper
    # ──────────────────────────────────────────────────────────────────

    def _add_action(self, menu, label: str, slot,
                    shortcut: QKeySequence | None = None) -> QAction:
        act = QAction(label, self)
        if shortcut:
            act.setShortcut(shortcut)
        act.triggered.connect(slot)
        menu.addAction(act)
        return act

    def _require_open(self) -> bool:
        if not self._engine.document:
            QMessageBox.information(self, "提示", "請先開啟一個 PDF 檔案。")
            return False
        return True

    # ──────────────────────────────────────────────────────────────────
    # Thumbnail management
    # ──────────────────────────────────────────────────────────────────

    def _start_thumbnail_loading(self) -> None:
        self._stop_thumbnail_loading()
        self._thumb_panel.set_page_count(self._engine.page_count())

        self._thumb_thread = QThread()
        self._thumb_worker = _ThumbnailWorker(self._engine, zoom=0.20)
        self._thumb_worker.moveToThread(self._thumb_thread)

        self._thumb_thread.started.connect(self._thumb_worker.run)
        self._thumb_worker.thumbnail_ready.connect(self._thumb_panel.update_thumbnail)
        # 只讓 worker 通知 thread 可以結束；生命週期完全由 _stop_thumbnail_loading 管理，
        # 不使用 deleteLater / _clear_thumb_refs，避免非同步回呼誤清新執行緒的參考。
        self._thumb_worker.finished.connect(self._thumb_thread.quit)

        self._thumb_thread.start()

    def _stop_thumbnail_loading(self) -> None:
        if self._thumb_worker:
            self._thumb_worker.stop()
        if self._thumb_thread:
            if self._thumb_thread.isRunning():
                self._thumb_thread.quit()
                self._thumb_thread.wait()   # 無限等待，確保執行緒真正停止再繼續
            self._thumb_thread = None
        self._thumb_worker = None

    def _reload_all(self) -> None:
        """Reload thumbnails and re-display current page after any document change."""
        self._current_page = max(0, min(self._current_page, self._engine.page_count() - 1))
        self._thumb_panel.clear()
        self._start_thumbnail_loading()
        self._display_page(self._current_page)

    # ──────────────────────────────────────────────────────────────────
    # Page display
    # ──────────────────────────────────────────────────────────────────

    def _display_page(self, index: int) -> None:
        if not self._engine.document:
            return
        if index < 0 or index >= self._engine.page_count():
            return
        self._current_page = index

        pix = self._engine.render_page_pixmap(index, zoom=1.5)
        if pix:
            img = QImage(
                pix.samples, pix.width, pix.height,
                pix.stride, QImage.Format.Format_RGB888,
            )
            qpix = QPixmap.fromImage(img)
            self._viewer.display_page(qpix, index, self._engine.page_count())

        self._thumb_panel.select_page(index)
        self._update_status()

    # ──────────────────────────────────────────────────────────────────
    # Signals from child widgets
    # ──────────────────────────────────────────────────────────────────

    def _on_thumb_selected(self, index: int) -> None:
        if index != self._current_page:
            self._display_page(index)

    def _on_viewer_page_changed(self, index: int) -> None:
        self._display_page(index)

    def _on_page_moved(self, from_idx: int, to_idx: int) -> None:
        """User reordered pages via drag-drop in thumbnail panel."""
        self._engine.move_page(from_idx, to_idx)
        # Update tracked current page index
        if self._current_page == from_idx:
            self._current_page = to_idx
        elif from_idx < self._current_page <= to_idx:
            self._current_page -= 1
        elif to_idx <= self._current_page < from_idx:
            self._current_page += 1
        self._reload_all()

    # ──────────────────────────────────────────────────────────────────
    # Actions
    # ──────────────────────────────────────────────────────────────────

    def _act_open(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "開啟 PDF", "", "PDF 檔案 (*.pdf)"
        )
        if not path:
            return
        self._stop_thumbnail_loading()
        if self._engine.open(path):
            self._current_page = 0
            self._thumb_panel.clear()
            self._viewer.clear()
            self._start_thumbnail_loading()
            self._display_page(0)
        else:
            QMessageBox.critical(self, "錯誤", "無法開啟此 PDF 檔案。")

    def _act_save(self) -> None:
        if not self._require_open():
            return
        if self._engine.filepath:
            if self._engine.save():
                self._status_lbl.setText(f"已儲存：{self._engine.filepath}")
            else:
                QMessageBox.critical(self, "錯誤", "儲存失敗。")
        else:
            self._act_save_as()

    def _act_save_as(self) -> None:
        if not self._require_open():
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "另存新檔", "", "PDF 檔案 (*.pdf)"
        )
        if not path:
            return
        if not path.lower().endswith(".pdf"):
            path += ".pdf"
        if self._engine.save_as(path):
            self._update_status()
            self._status_lbl.setText(f"已另存為：{path}")
        else:
            QMessageBox.critical(self, "錯誤", "儲存失敗。")

    def _act_close_pdf(self) -> None:
        self._stop_thumbnail_loading()
        self._engine.close()
        self._thumb_panel.clear()
        self._viewer.clear()
        self._current_page = 0
        self._status_lbl.setText("尚未開啟 PDF")
        self.setWindowTitle("PDF Editor")

    def _act_add_pages(self) -> None:
        if not self._require_open():
            return
        path, _ = QFileDialog.getOpenFileName(
            self, "選擇來源 PDF", "", "PDF 檔案 (*.pdf)"
        )
        if not path:
            return

        from ui.dialogs import PageSelectDialog
        dlg = PageSelectDialog(path, self)
        if dlg.exec():
            pages = dlg.get_selected_pages()
            if not pages:
                QMessageBox.information(self, "提示", "未選取任何頁面。")
                return
            insert_at = self._current_page + 1
            if self._engine.insert_pages(path, pages, insert_at):
                self._current_page = insert_at
                self._reload_all()
                QMessageBox.information(
                    self, "完成",
                    f"已在第 {insert_at + 1} 頁位置插入 {len(pages)} 頁。"
                )
            else:
                QMessageBox.critical(self, "錯誤", "插入頁面失敗。")

    def _act_merge(self) -> None:
        if not self._require_open():
            return
        path, _ = QFileDialog.getOpenFileName(
            self, "選擇要合併的 PDF", "", "PDF 檔案 (*.pdf)"
        )
        if not path:
            return
        if self._engine.merge_pdf(path):
            self._reload_all()
            name = os.path.basename(path)
            QMessageBox.information(self, "完成", f"已將「{name}」合併到末尾。")
        else:
            QMessageBox.critical(self, "錯誤", "合併失敗。")

    def _act_delete(self) -> None:
        if not self._require_open():
            return
        selected = self._thumb_panel.get_selected_indices()
        if not selected:
            QMessageBox.information(self, "提示", "請先在左側縮圖面板中選取要刪除的頁面。")
            return
        if self._engine.page_count() <= len(selected):
            QMessageBox.warning(self, "警告", "不能刪除所有頁面。")
            return
        reply = QMessageBox.question(
            self, "確認刪除",
            f"確定要刪除選取的 {len(selected)} 頁嗎？此操作可在儲存前復原。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._engine.delete_pages(selected)
            self._current_page = min(self._current_page, self._engine.page_count() - 1)
            self._reload_all()

    def _act_rotate(self, angle: int) -> None:
        if not self._require_open():
            return
        selected = self._thumb_panel.get_selected_indices()
        if not selected:
            selected = [self._current_page]  # fallback: current page
        self._engine.rotate_pages(selected, angle)
        self._reload_all()

    def _act_split(self) -> None:
        if not self._require_open():
            return
        out_dir = QFileDialog.getExistingDirectory(self, "選擇分割輸出資料夾")
        if not out_dir:
            return
        base = os.path.splitext(
            os.path.basename(self._engine.filepath or "output")
        )[0]
        files = self._engine.split_by_n(10, out_dir, base)
        if not files:
            QMessageBox.critical(self, "錯誤", "分割失敗。")
            return

        names = "\n".join(f"  • {os.path.basename(f)}" for f in files)
        msg = QMessageBox(self)
        msg.setWindowTitle("分割完成")
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setText(f"已分割為 <b>{len(files)}</b> 個檔案：")
        msg.setInformativeText(f"{names}\n\n輸出資料夾：{out_dir}")
        open_btn = msg.addButton("開啟資料夾", QMessageBox.ButtonRole.ActionRole)
        msg.addButton(QMessageBox.StandardButton.Ok)
        msg.exec()
        if msg.clickedButton() == open_btn:
            subprocess.Popen(["explorer", os.path.normpath(out_dir)])

    # ──────────────────────────────────────────────────────────────────
    # Status
    # ──────────────────────────────────────────────────────────────────

    def _update_status(self) -> None:
        if self._engine.document:
            name = os.path.basename(self._engine.filepath or "未命名")
            total = self._engine.page_count()
            cur = self._current_page + 1
            self._status_lbl.setText(f"{name}  │  第 {cur} 頁，共 {total} 頁")
            self.setWindowTitle(f"PDF Editor — {name}")

    # ──────────────────────────────────────────────────────────────────
    # Cleanup
    # ──────────────────────────────────────────────────────────────────

    def closeEvent(self, event) -> None:  # noqa: N802
        self._stop_thumbnail_loading()
        self._engine.close()
        super().closeEvent(event)
