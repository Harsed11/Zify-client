from PySide6.QtCore import Qt, QRectF
from PySide6.QtWidgets import QAbstractButton
from PySide6.QtGui import QPainter, QColor

from vpn_configurator.ui import theme


class SwitchToggle(QAbstractButton):
    """On/off switch used across the settings page."""

    W = 46
    H = 24
    KNOB = 18

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(self.W, self.H)
        self.setCursor(Qt.PointingHandCursor)
        self.setCheckable(True)
        self.setAttribute(Qt.WA_StyledBackground, False)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        green = QColor(theme.current["GREEN"])
        off = QColor(255, 255, 255, 22)

        checked = self.isChecked()
        track = green if checked else off
        if self.underMouse():
            track = track.lighter(114)

        p.setPen(Qt.NoPen)
        p.setBrush(track)
        p.drawRoundedRect(QRectF(0, 0, self.W, self.H), self.H / 2, self.H / 2)

        knob = QColor("#FFFFFF")
        if self.isDown():
            knob = knob.lighter(88)
        x = 3 if not checked else (self.W - 3 - self.KNOB)
        p.setBrush(knob)
        p.drawEllipse(QRectF(x, 3, self.KNOB, self.KNOB))
