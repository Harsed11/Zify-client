from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QGraphicsOpacityEffect, QGraphicsDropShadowEffect,
)
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QPoint, QEasingCurve
from PySide6.QtGui import QColor

from vpn_configurator.ui import theme
from vpn_configurator.ui.theme import hex_rgba

TYPE_ICONS = {"success": "\u2713", "warning": "\u26A0", "error": "\u2715"}

SLIDE_MS = 650
HOLD_MS = 1000
FADE_MS = 320


def _type_color(kind):
    t = theme.current
    return {
        "success": t["GREEN"],
        "warning": t["YELLOW"],
        "error": t["RED"],
    }.get(kind, t["ACCENT"])


class Toast(QWidget):
    def __init__(self, parent, message="", kind="success"):
        super().__init__(parent)
        self._kind = kind if kind in TYPE_ICONS else "success"
        self._running = []

        self.setFixedHeight(56)
        self.setMinimumWidth(320)
        self.setMaximumWidth(440)

        outer = QVBoxLayout()
        outer.setContentsMargins(0, 0, 0, 0)
        self.setLayout(outer)

        self._card = QFrame(self)
        self._card.setObjectName("toastCard")
        layout = QHBoxLayout()
        layout.setContentsMargins(12, 0, 18, 0)
        layout.setSpacing(12)
        self._card.setLayout(layout)

        self.lbl_icon = QLabel()
        self.lbl_icon.setFixedSize(28, 28)
        self.lbl_icon.setAlignment(Qt.AlignCenter)

        self.lbl_msg = QLabel(message)
        self.lbl_msg.setWordWrap(True)

        layout.addWidget(self.lbl_icon)
        layout.addWidget(self.lbl_msg, 1)
        outer.addWidget(self._card)

        self._shadow = QGraphicsDropShadowEffect(self._card)
        self._shadow.setBlurRadius(34)
        self._shadow.setColor(QColor(0, 0, 0, 140))
        self._shadow.setOffset(0, 10)
        self._card.setGraphicsEffect(self._shadow)

        self._opacity_effect = QGraphicsOpacityEffect(self)
        self._opacity_effect.setOpacity(0.0)
        self.setGraphicsEffect(self._opacity_effect)

        self._hold_timer = QTimer(self)
        self._hold_timer.setSingleShot(True)
        self._hold_timer.timeout.connect(self._fade_out)

        self._apply_style()
        self.hide()

    def _stop_all(self):
        for anim in self._running:
            anim.stop()
            anim.deleteLater()
        self._running = []
        self._hold_timer.stop()

    def _start_anim(self, anim):
        anim.setParent(self)
        self._running.append(anim)
        anim.start()
        return anim

    def _on_anim_finished(self, anim):
        if anim in self._running:
            self._running.remove(anim)
        anim.deleteLater()

    def notify(self, message, kind="success"):
        self._kind = kind if kind in TYPE_ICONS else "success"
        self.lbl_msg.setText(message)
        self._apply_style()

        p = self.parent()
        if p:
            self.adjustSize()
            w = self.width()
            self._end_x = p.width() - w - 24
            self._end_y = p.height() - self.height() - 24
            self._start_y = self._end_y + 48
            self.move(self._end_x, self._start_y)

        self._stop_all()
        self._opacity_effect.setOpacity(0.0)
        self.show()
        self.raise_()

        slide = QPropertyAnimation(self, b"pos")
        slide.setDuration(SLIDE_MS)
        slide.setStartValue(QPoint(self._end_x, self._start_y))
        slide.setEndValue(QPoint(self._end_x, self._end_y))
        slide.setEasingCurve(QEasingCurve.OutCubic)
        slide.finished.connect(lambda: self._on_anim_finished(slide))
        self._start_anim(slide)

        fade_in = QPropertyAnimation(self._opacity_effect, b"opacity")
        fade_in.setDuration(SLIDE_MS)
        fade_in.setStartValue(0.0)
        fade_in.setEndValue(1.0)
        fade_in.setEasingCurve(QEasingCurve.OutCubic)
        fade_in.finished.connect(lambda: self._on_anim_finished(fade_in))
        self._start_anim(fade_in)

        self._hold_timer.start(SLIDE_MS + HOLD_MS)

    def _fade_out(self):
        fade_out = QPropertyAnimation(self._opacity_effect, b"opacity")
        fade_out.setDuration(FADE_MS)
        fade_out.setStartValue(1.0)
        fade_out.setEndValue(0.0)
        fade_out.finished.connect(lambda: self._on_anim_finished(fade_out))
        fade_out.finished.connect(self.hide)
        self._start_anim(fade_out)

        sink = QPropertyAnimation(self, b"pos")
        sink.setDuration(FADE_MS)
        sink.setStartValue(QPoint(self._end_x, self._end_y))
        sink.setEndValue(QPoint(self._end_x, self._end_y + 14))
        sink.finished.connect(lambda: self._on_anim_finished(sink))
        self._start_anim(sink)

    def _apply_style(self):
        color = _type_color(self._kind)
        self.lbl_icon.setText(TYPE_ICONS.get(self._kind, "\u2713"))
        self.lbl_icon.setStyleSheet(
            f"background: {hex_rgba(color, 0.16)}; color: {color}; "
            f"border-radius: 14px; font-size: 13px; font-weight: bold;"
        )
        self.lbl_msg.setStyleSheet(
            f"color: {theme.current['TEXT_PRI']}; font-size: 12px;"
        )
        self._card.setStyleSheet(
            f"QFrame#toastCard {{ background-color: {theme.current['TOAST_BG']}; "
            f"border: 1px solid {hex_rgba(color, 0.4)}; border-radius: 14px; }}"
        )

    def show_toast(self):
        self.notify(self.lbl_msg.text(), self._kind)
