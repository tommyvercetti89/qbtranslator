"""Full-screen screen region selector for OCR."""

from __future__ import annotations

from PySide6.QtCore import QPoint, QRect, Qt, Signal
from PySide6.QtGui import QColor, QFont, QGuiApplication, QPainter, QPen
from PySide6.QtWidgets import QWidget

from qbtranslator.core.win32util import get_cursor_pos
from qbtranslator.i18n import t

ACCENT = "#4da3ff"
TEXT = "#ffffff"
MUTED = "#c7d2de"


class RegionSelector(QWidget):
    region_selected = Signal(object)
    cancelled = Signal()

    def __init__(self) -> None:
        super().__init__(None)
        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setCursor(Qt.CrossCursor)
        self.setMouseTracking(True)

        geometry = self._virtual_geometry()
        self.setGeometry(*geometry)
        self._start: QPoint | None = None
        self._current: QPoint | None = None
        self._start_physical: tuple[int, int] | None = None
        self._done = False

    @staticmethod
    def _virtual_geometry() -> tuple[int, int, int, int]:
        screens = QGuiApplication.screens()
        if not screens:
            return 0, 0, 1920, 1080
        geometry = QRect()
        for screen in screens:
            geometry = geometry.united(screen.geometry())
        return geometry.x(), geometry.y(), geometry.width(), geometry.height()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self.raise_()
        self.activateWindow()
        self.setFocus(Qt.OtherFocusReason)

    def _selection_rect(self) -> QRect:
        if self._start is None or self._current is None:
            return QRect()
        return QRect(self._start, self._current).normalized()

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 125))

        selection = self._selection_rect()
        if not selection.isNull():
            painter.setCompositionMode(QPainter.CompositionMode_Clear)
            painter.fillRect(selection, Qt.transparent)
            painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
            painter.setPen(QPen(QColor(ACCENT), 2))
            painter.drawRect(selection.adjusted(0, 0, -1, -1))

        font = QFont("Segoe UI Semibold", 13)
        painter.setFont(font)
        painter.setPen(QColor(TEXT))
        painter.drawText(
            QRect(0, 16, self.width(), 30),
            Qt.AlignHCenter | Qt.AlignVCenter,
            t("ocr.selection_hint"),
        )
        painter.setFont(QFont("Segoe UI", 9))
        painter.setPen(QColor(MUTED))
        painter.drawText(
            QRect(0, self.height() - 40, self.width(), 24),
            Qt.AlignHCenter | Qt.AlignVCenter,
            t("ocr.cancel_hint"),
        )

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.RightButton:
            self._cancel()
            return
        if event.button() == Qt.LeftButton:
            self._start = event.position().toPoint()
            self._current = self._start
            self._start_physical = get_cursor_pos()
            self.update()

    def mouseMoveEvent(self, event) -> None:
        if self._start is not None and event.buttons() & Qt.LeftButton:
            self._current = event.position().toPoint()
            self.update()

    def mouseReleaseEvent(self, event) -> None:
        if event.button() != Qt.LeftButton or self._start is None:
            return
        self._current = event.position().toPoint()
        selection = self._selection_rect()
        if selection.width() < 12 or selection.height() < 12:
            self._cancel()
            return
        start_physical = self._start_physical or get_cursor_pos()
        end_physical = get_cursor_pos()
        left, right = sorted((start_physical[0], end_physical[0]))
        top, bottom = sorted((start_physical[1], end_physical[1]))
        if right - left < 12 or bottom - top < 12:
            self._cancel()
            return
        self._done = True
        region = (left, top, right - left, bottom - top)
        self.hide()
        self.region_selected.emit(region)
        self.deleteLater()

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key_Escape:
            self._cancel()
            return
        super().keyPressEvent(event)

    def _cancel(self) -> None:
        if self._done:
            return
        self._done = True
        self.hide()
        self.cancelled.emit()
        self.deleteLater()
