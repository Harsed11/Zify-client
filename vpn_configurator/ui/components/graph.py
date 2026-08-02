import math

from PySide6.QtCore import Qt, QPointF, QTimer
from PySide6.QtWidgets import QWidget, QToolTip
from PySide6.QtGui import (
    QPainter, QPainterPath, QColor, QLinearGradient, QPen,
)

from vpn_configurator.ui import theme


class TrafficGraph(QWidget):
    _COLOR_KEY = {"download": "CYAN", "upload": "RED", "ping": "GREEN"}

    def __init__(self, parent=None, mode="download"):
        super().__init__(parent)
        self.mode = mode
        self._data = [0.0] * 150
        self._max_val = 1.0
        self._smooth_val = 0.0
        self._color = QColor(theme.current[self._COLOR_KEY.get(mode, "CYAN")])
        self._hover_index = -1
        self._phase = 0.0
        self.setMouseTracking(True)
        self.setMinimumHeight(84)

        self._pulse_timer = QTimer(self)
        self._pulse_timer.setInterval(16)
        self._pulse_timer.timeout.connect(self._pulse_tick)

    def reset(self):
        self._data = [0.0] * 150
        self._max_val = 1.0
        self._smooth_val = 0.0
        self._hover_index = -1
        self._pulse_timer.stop()
        self.update()

    def add_point(self, down, up):
        raw = down if self.mode == "download" else up
        self.add_value(raw)

    def add_value(self, raw):
        self._smooth_val += (raw - self._smooth_val) * 0.15
        self._data.append(self._smooth_val)
        if len(self._data) > 150:
            self._data.pop(0)
        self._max_val = max(max(self._data), 1.0)
        if raw > 0 and not self._pulse_timer.isActive():
            self._pulse_timer.start()
        self.update()

    def _pulse_tick(self):
        self._phase += 0.18
        if all(v <= 0 for v in self._data[-5:]):
            self._pulse_timer.stop()
        self.update()

    def _catmull_to_cubic(self, p0, p1, p2, p3):
        cp1 = QPointF(p1.x() + (p2.x() - p0.x()) / 6, p1.y() + (p2.y() - p0.y()) / 6)
        cp2 = QPointF(p2.x() - (p3.x() - p1.x()) / 6, p2.y() - (p3.y() - p1.y()) / 6)
        return cp1, cp2

    def _smooth_path(self, points):
        path = QPainterPath()
        n = len(points)
        if n < 2:
            if n == 1:
                path.moveTo(points[0])
            return path
        path.moveTo(points[0])
        for i in range(n - 1):
            p0 = points[i - 1] if i > 0 else points[i]
            p1 = points[i]
            p2 = points[i + 1]
            p3 = points[i + 2] if i + 2 < n else p2
            cp1, cp2 = self._catmull_to_cubic(p0, p1, p2, p3)
            path.cubicTo(cp1, cp2, p2)
        return path

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        c = self._color

        pen = QPen(QColor(255, 255, 255, 14), 1)
        painter.setPen(pen)
        for i in range(1, 4):
            y = h * i // 4
            painter.drawLine(0, y, w, y)

        pad_l, pad_r, pad_t, pad_b = 10, 10, 10, 16
        plot_w = w - pad_l - pad_r
        plot_h = h - pad_t - pad_b
        baseline_y = h - pad_b

        if not self._data or all(v == 0 for v in self._data):
            pen_dash = QPen(QColor(c.red(), c.green(), c.blue(), 50), 1.2, Qt.DashLine)
            painter.setPen(pen_dash)
            painter.drawLine(pad_l, baseline_y, w - pad_r, baseline_y)
            painter.setPen(QColor(theme.current["TEXT_DIM"]))
            font = painter.font()
            font.setPointSize(8)
            painter.setFont(font)
            painter.drawText(
                self.rect(), Qt.AlignCenter,
                "WAITING FOR LATENCY" if self.mode == "ping" else "WAITING FOR TRAFFIC",
            )
            painter.end()
            return

        visible = self._data[-150:] if len(self._data) > 150 else self._data
        n_visible = len(visible)
        points = []
        for i, val in enumerate(visible):
            x = pad_l + (i / max(n_visible - 1, 1)) * plot_w
            norm = val / self._max_val
            y = pad_t + plot_h - min(norm, 1.0) * plot_h
            points.append(QPointF(x, max(y, pad_t)))

        path = self._smooth_path(points)

        grad = QLinearGradient(0, pad_t, 0, baseline_y)
        grad.setColorAt(0.0, QColor(c.red(), c.green(), c.blue(), 26))
        grad.setColorAt(1.0, QColor(c.red(), c.green(), c.blue(), 0))
        painter.setBrush(grad)
        painter.setPen(Qt.NoPen)
        fill_path = QPainterPath(path)
        fill_path.lineTo(points[-1].x(), baseline_y)
        fill_path.lineTo(points[0].x(), baseline_y)
        fill_path.closeSubpath()
        painter.drawPath(fill_path)

        pen_glow = QPen(QColor(c.red(), c.green(), c.blue(), 40), 5)
        pen_glow.setCapStyle(Qt.RoundCap)
        painter.setBrush(Qt.NoBrush)
        painter.setPen(pen_glow)
        painter.drawPath(path)

        pen_core = QPen(c, 2)
        pen_core.setCapStyle(Qt.RoundCap)
        pen_core.setJoinStyle(Qt.RoundJoin)
        painter.setPen(pen_core)
        painter.drawPath(path)

        last_val = visible[-1]
        if last_val > 0:
            lp = points[-1]
            pulse_r = 4.0 + 2.0 * (0.5 + 0.5 * math.sin(self._phase))
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(c.red(), c.green(), c.blue(), 40))
            painter.drawEllipse(lp, pulse_r + 6, pulse_r + 6)
            painter.setBrush(c)
            painter.drawEllipse(lp, 3.2, 3.2)

        if 0 <= self._hover_index < len(points):
            pt = points[self._hover_index]
            pen_dash = QPen(QColor("#8A8F9F"), 1, Qt.DashLine)
            painter.setPen(pen_dash)
            painter.drawLine(int(pt.x()), pad_t, int(pt.x()), baseline_y)
            painter.setPen(Qt.NoPen)
            painter.setBrush(c)
            painter.drawEllipse(pt, 3.5, 3.5)
            painter.setBrush(QColor(c.red(), c.green(), c.blue(), 35))
            painter.drawEllipse(pt, 9, 9)

        painter.end()

    def mouseMoveEvent(self, event):
        w = self.width()
        pad_l, pad_r = 10, 10
        plot_w = w - pad_l - pad_r
        visible = self._data[-150:] if len(self._data) > 150 else self._data
        if not visible or plot_w <= 0:
            return
        rel_x = event.position().x() - pad_l
        idx = int((rel_x / plot_w) * (len(visible) - 1))
        idx = max(0, min(idx, len(visible) - 1))
        self._hover_index = idx
        val = visible[idx]
        label = f"{'DL' if self.mode == 'download' else 'UL'}: {self._fmt(val)}"
        QToolTip.showText(event.globalPosition().toPoint(), label, self)
        self.update()
        super().mouseMoveEvent(event)

    def leaveEvent(self, event):
        self._hover_index = -1
        QToolTip.hideText()
        self.update()
        super().leaveEvent(event)

    def _fmt(self, val):
        if self.mode == "ping":
            return f"PING: {int(val)} ms"
        if val >= 1024 * 1024:
            return f"{val / (1024 * 1024):.1f} GB/s"
        if val >= 1024:
            return f"{val / 1024:.1f} MB/s"
        if val >= 1:
            return f"{val:.1f} KB/s"
        return f"{int(val * 1024)} B/s"
