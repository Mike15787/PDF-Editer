"""
PDF Engine — wraps PyMuPDF (fitz) for all PDF operations.
MuPDF is a C library, so rendering and manipulation are very fast.
"""
from __future__ import annotations

import os
import tempfile
from typing import List, Optional, Tuple

import fitz  # PyMuPDF


class PDFEngine:
    def __init__(self) -> None:
        self.document: Optional[fitz.Document] = None
        self.filepath: Optional[str] = None

    # ------------------------------------------------------------------
    # Open / Close
    # ------------------------------------------------------------------

    def open(self, filepath: str) -> bool:
        try:
            if self.document:
                self.document.close()
            self.document = fitz.open(filepath)
            self.filepath = filepath
            return True
        except Exception as e:
            print(f"[PDFEngine] open error: {e}")
            return False

    def close(self) -> None:
        if self.document:
            self.document.close()
            self.document = None
            self.filepath = None

    # ------------------------------------------------------------------
    # Info
    # ------------------------------------------------------------------

    def page_count(self) -> int:
        return len(self.document) if self.document else 0

    def page_size(self, index: int) -> Tuple[float, float]:
        if not self.document or index >= len(self.document):
            return (0.0, 0.0)
        r = self.document[index].rect
        return (r.width, r.height)

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def render_page_pixmap(self, index: int, zoom: float = 1.0) -> Optional[fitz.Pixmap]:
        """Return a fitz.Pixmap (RGB, no alpha).  Use .samples for raw bytes."""
        if not self.document or index < 0 or index >= len(self.document):
            return None
        page = self.document[index]
        mat = fitz.Matrix(zoom, zoom)
        return page.get_pixmap(matrix=mat, alpha=False)

    # ------------------------------------------------------------------
    # Page operations
    # ------------------------------------------------------------------

    def delete_pages(self, indices: List[int]) -> bool:
        if not self.document:
            return False
        for idx in sorted(set(indices), reverse=True):
            if 0 <= idx < len(self.document):
                self.document.delete_page(idx)
        return True

    def rotate_pages(self, indices: List[int], angle: int) -> bool:
        """angle: +90 (CW), -90 / 270 (CCW), 180."""
        if not self.document:
            return False
        angle = angle % 360
        for idx in indices:
            if 0 <= idx < len(self.document):
                page = self.document[idx]
                new_rot = (page.rotation + angle) % 360
                page.set_rotation(new_rot)
        return True

    def move_page(self, from_idx: int, to_idx: int) -> bool:
        """Move one page to a new position (0-based)."""
        if not self.document:
            return False
        if from_idx == to_idx:
            return True
        try:
            self.document.move_page(from_idx, to_idx)
            return True
        except Exception as e:
            print(f"[PDFEngine] move_page error: {e}")
            return False

    # ------------------------------------------------------------------
    # Insert / Merge
    # ------------------------------------------------------------------

    def insert_pages(self, source_path: str, page_indices: List[int], insert_at: int) -> bool:
        """Insert specific pages from *source_path* at *insert_at* position."""
        if not self.document:
            return False
        try:
            src = fitz.open(source_path)
            # Build a temp doc with only the selected pages (preserves order)
            tmp = fitz.open()
            for idx in page_indices:
                if 0 <= idx < len(src):
                    tmp.insert_pdf(src, from_page=idx, to_page=idx)
            src.close()
            self.document.insert_pdf(tmp, start_at=insert_at)
            tmp.close()
            return True
        except Exception as e:
            print(f"[PDFEngine] insert_pages error: {e}")
            return False

    def merge_pdf(self, source_path: str) -> bool:
        """Append all pages of *source_path* to the end of the current document."""
        if not self.document:
            return False
        try:
            src = fitz.open(source_path)
            self.document.insert_pdf(src)
            src.close()
            return True
        except Exception as e:
            print(f"[PDFEngine] merge_pdf error: {e}")
            return False

    # ------------------------------------------------------------------
    # Split
    # ------------------------------------------------------------------

    def split_by_n(self, n: int, output_dir: str, base_name: str) -> List[str]:
        """Split document into files of *n* pages each.  Returns list of file paths."""
        if not self.document:
            return []
        output_files: List[str] = []
        total = len(self.document)
        part = 1
        for start in range(0, total, n):
            end = min(start + n - 1, total - 1)
            chunk = fitz.open()
            chunk.insert_pdf(self.document, from_page=start, to_page=end)
            out_path = os.path.join(output_dir, f"{base_name}_part{part:03d}.pdf")
            chunk.save(out_path, garbage=4, deflate=True)
            chunk.close()
            output_files.append(out_path)
            part += 1
        return output_files

    # ------------------------------------------------------------------
    # Save
    # ------------------------------------------------------------------

    def save(self, filepath: Optional[str] = None) -> bool:
        if not self.document:
            return False
        save_path = filepath or self.filepath
        if not save_path:
            return False
        try:
            dir_path = os.path.dirname(os.path.abspath(save_path)) or "."
            fd, tmp_path = tempfile.mkstemp(suffix=".pdf", dir=dir_path)
            os.close(fd)
            self.document.save(tmp_path, garbage=4, deflate=True)
            os.replace(tmp_path, save_path)
            self.filepath = save_path
            return True
        except Exception as e:
            print(f"[PDFEngine] save error: {e}")
            try:
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
            except Exception:
                pass
            return False

    def save_as(self, filepath: str) -> bool:
        return self.save(filepath)
