import math
from enum import Enum

from PySide6.QtCore import Qt, QRectF, QPointF, QPoint, QTimer, QVariantAnimation, QPropertyAnimation, QRect, QEasingCurve
from PySide6.QtWidgets import QAbstractButton, QGraphicsDropShadowEffect
from PySide6.QtGui import QPainter, QColor, QLinearGradient, QPen, QFont, QFontMetrics

from vpn_configurator.ui import theme


class ConnectState(Enum):
    IDLE = 0
    CONNECTING = 1
    CONNECTED = 2


def _lerp_color(a, b, t):
    return QColor(
        int(a.red() + (b.red() - a.red()) * t),
        int(a.green() + (b.green() - a.green()) * t),
        int(a.blue() + (b.blue() - a.blue()) * t),
    )


class ConnectButton(QAbstractButton):
    """CONNECT / DISCONNECT button with smooth state transitions."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(320, 64)
        self.setCursor(Qt.PointingHandCursor)
        self._state = ConnectState.IDLE
        self._from = self._palette(ConnectState.IDLE)
        self._to = self._palette(ConnectState.IDLE)
        self._blend = 1.0
        self._spin = 0.0
        self._pulse = 0.0
        self._hovered = False

        self._glow = QGraphicsDropShadowEffect(self)
        self._glow.setBlurRadius(30)
        self._glow.setOffset(0, 8)
        self._glow.setColor(QColor(0, 0, 0, 130))
        self.setGraphicsEffect(self._glow)

        self._state_anim = QVariantAnimation(self)
        self._state_anim.setDuration(280)
        self._state_anim.setEasingCurve(QEasingCurve.OutCubic)
        self._state_anim.valueChanged.connect(self._on_blend)

        self._spin_timer = QTimer(self)
        self._spin_timer.setInterval(16)
        self._spin_timer.timeout.connect(self._spin_tick)

        self._pulse_timer = QTimer(self)
        self._pulse_timer.setInterval(40)
        self._pulse_timer.timeout.connect(self._pulse_tick)

    @staticmethod
    def _palette(state):
        t = theme.current
        if state is ConnectState.CONNECTING:
            return QColor(t["YELLOW"]), QColor(t["ACCENT_LIGHT"])
        if state is ConnectState.CONNECTED:
            return QColor(t["RED"]), QColor("#FF9A62")
        return QColor(t["GLOW_CONNECT"]), QColor(t["CYAN"])

    def state(self):
        return self._state

    def set_state(self, state):
        if state == self._state:
            return
        self._from = self._palette(self._state)
        self._to = self._palette(state)
        self._state = state
        self._blend = 0.0
        self._state_anim.stop()
        self._state_anim.setStartValue(0.0)
        self._state_anim.setEndValue(1.0)
        self._state_anim.start()

        if state is ConnectState.CONNECTING:
            self._spin_timer.start()
        else:
            self._spin_timer.stop()
        if state is ConnectState.CONNECTED:
            self._pulse_timer.start()
        else:
            self._pulse_timer.stop()
        if state is ConnectState.IDLE:
            c = QColor(theme.current["ACCENT"])
            c.setAlpha(120)
            self._glow.setColor(c)
        elif state is ConnectState.CONNECTING:
            c = QColor(theme.current["YELLOW"])
            c.setAlpha(95)
            self._glow.setColor(c)
        self.update()

    def _on_blend(self, value):
        self._blend = float(value)
        self.update()

    def _spin_tick(self):
        self._spin += 0.14
        self.update()

    def _pulse_tick(self):
        self._pulse += 0.09
        c1, c2 = self._palette(self._state)
        c = _lerp_color(c1, c2, 0.5)
        c.setAlpha(100 + int(55 * (0.5 + 0.5 * math.sin(self._pulse))))
        self._glow.setColor(c)

    def enterEvent(self, event):
        self._hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hovered = False
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event):
        c1 = _lerp_color(self._from[0], self._to[0], self._blend)
        c2 = _lerp_color(self._from[1], self._to[1], self._blend)

        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)

        grad = QLinearGradient(rect.topLeft(), rect.topRight())
        grad.setColorAt(0.0, c1)
        grad.setColorAt(1.0, c2)
        p.setPen(Qt.NoPen)
        p.setBrush(grad)
        p.drawRoundedRect(rect, 32, 32)

        if self.isDown():
            p.setBrush(QColor(255, 255, 255, 20))
            p.drawRoundedRect(rect, 32, 32)
        elif self._hovered:
            p.setBrush(QColor(255, 255, 255, 12))
            p.drawRoundedRect(rect, 32, 32)

        labels = {
            ConnectState.IDLE: "CONNECT",
            ConnectState.CONNECTING: "CONNECTING",
            ConnectState.CONNECTED: "DISCONNECT",
        }
        label = labels[self._state]

        font = QFont("Segoe UI")
        font.setPixelSize(15)
        font.setWeight(QFont.Weight.DemiBold)
        p.setFont(font)
        fm = QFontMetrics(font)

        if self._state is ConnectState.CONNECTING:
            tw = fm.horizontalAdvance(label)
            cx = self.width() / 2 - tw / 2 - 26
            cy = self.height() / 2
            p.setPen(QPen(QColor(255, 255, 255, 230), 3, Qt.SolidLine, Qt.RoundCap))
            p.setBrush(Qt.NoBrush)
            p.drawArc(QRectF(cx - 8, cy - 8, 16, 16), int(-self._spin * 16), int(110 * 16))
            p.setPen(QColor("#FFFFFF"))
            p.drawText(self.rect(), Qt.AlignCenter, label)
        else:
            tracking = 3
            widths = [fm.horizontalAdvance(ch) for ch in label]
            total = sum(widths) + tracking * (len(label) - 1)
            x = (self.width() - total) / 2
            y = (self.height() + fm.ascent() - fm.descent()) / 2
            p.setPen(QColor("#FFFFFF"))
            for ch, wch in zip(label, widths):
                p.drawText(QPointF(x, y), ch)
                x += wch + tracking

    def bounce(self):
        g = self.geometry()
        a = QPropertyAnimation(self, b"geometry")
        a.setDuration(380)
        a.setKeyValueAt(0.0, g)
        a.setKeyValueAt(0.2, QRect(g.x() + 5, g.y() + 5, g.width() - 10, g.height() - 10))
        a.setKeyValueAt(0.5, QRect(g.x() - 3, g.y() - 3, g.width() + 6, g.height() + 6))
        a.setKeyValueAt(0.7, QRect(g.x() + 2, g.y() + 2, g.width() - 4, g.height() - 4))
        a.setKeyValueAt(1.0, g)
        a.start(QPropertyAnimation.DeleteWhenStopped)

        b = QPropertyAnimation(self._glow, b"blurRadius")
        b.setDuration(380)
        b.setKeyValueAt(0.0, self._glow.blurRadius())
        b.setKeyValueAt(0.4, 54)
        b.setKeyValueAt(1.0, 36 if self._state is ConnectState.CONNECTING else 30)
        b.start(QPropertyAnimation.DeleteWhenStopped)

    def shake(self):
        g = self.geometry()
        a = QPropertyAnimation(self, b"pos")
        a.setDuration(420)
        a.setKeyValueAt(0.0, g.topLeft())
        a.setKeyValueAt(0.15, QPoint(g.x() + 8, g.y()))
        a.setKeyValueAt(0.30, QPoint(g.x() - 8, g.y()))
        a.setKeyValueAt(0.45, QPoint(g.x() + 6, g.y()))
        a.setKeyValueAt(0.60, QPoint(g.x() - 6, g.y()))
        a.setKeyValueAt(0.80, QPoint(g.x() + 3, g.y()))
        a.setKeyValueAt(1.0, g.topLeft())
        a.start(QPropertyAnimation.DeleteWhenStopped)
