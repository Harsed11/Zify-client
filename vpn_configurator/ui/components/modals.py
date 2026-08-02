import io

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QApplication, QFrame, QGraphicsDropShadowEffect, QWidget,
)
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QPoint, QTimer
from PySide6.QtCore import QRectF
from PySide6.QtGui import QColor, QPixmap, QPainter, QLinearGradient, QFont

from vpn_configurator.ui import theme
from vpn_configurator.ui.theme import ghost_btn_qss, hex_rgba


def _make_shadow(widget, blur=60, y=16, alpha=180):
    shadow = QGraphicsDropShadowEffect(widget)
    shadow.setBlurRadius(blur)
    shadow.setOffset(0, y)
    shadow.setColor(QColor(0, 0, 0, alpha))
    widget.setGraphicsEffect(shadow)


def _animate_in(dialog):
    """Slide-up + fade-in on dialog open."""
    from PySide6.QtWidgets import QGraphicsOpacityEffect
    eff = QGraphicsOpacityEffect(dialog)
    dialog.setGraphicsEffect(eff)
    eff.setOpacity(0.0)

    start = dialog.pos() + QPoint(0, 24)
    dialog.move(start)

    fade = QPropertyAnimation(eff, b"opacity", dialog)
    fade.setDuration(220)
    fade.setStartValue(0.0)
    fade.setEndValue(1.0)
    fade.setEasingCurve(QEasingCurve.OutCubic)

    slide = QPropertyAnimation(dialog, b"pos", dialog)
    slide.setDuration(220)
    slide.setStartValue(start)
    slide.setEndValue(start - QPoint(0, 24))
    slide.setEasingCurve(QEasingCurve.OutCubic)

    fade.finished.connect(lambda: dialog.setGraphicsEffect(None))
    fade.start()
    slide.start()


class _BaseDialog(QDialog):
    """Frameless rounded dialog base with shadow and slide-in animation."""

    def __init__(self, parent=None, width=500, height=260):
        super().__init__(parent)
        t = theme.current
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowFlag(Qt.FramelessWindowHint)
        self.setFixedSize(width, height)

        outer = QVBoxLayout()
        outer.setContentsMargins(20, 20, 20, 20)
        self.setLayout(outer)

        self.frame = QFrame(self)
        self.frame.setObjectName("dialogFrame")
        self.frame.setStyleSheet(
            f"QFrame#dialogFrame {{ background-color: {t['DIALOG_BG']}; "
            f"border: 1px solid {t['BORDER_HOVER']}; border-radius: 20px; }}"
        )
        _make_shadow(self.frame)
        outer.addWidget(self.frame)

        self.fl = QVBoxLayout()
        self.fl.setContentsMargins(28, 24, 28, 24)
        self.fl.setSpacing(14)
        self.frame.setLayout(self.fl)

    def showEvent(self, event):
        super().showEvent(event)
        QTimer.singleShot(0, lambda: _animate_in(self))

    def _accent_btn(self, text):
        t = theme.current
        acc = QColor(t["ACCENT"])
        h1 = acc.lighter(112).name()
        h2 = acc.lighter(128).name()
        btn = QPushButton(text)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setDefault(True)
        btn.setStyleSheet(
            f"QPushButton {{ background: {t['GRAD_ACCENT']}; color: white; border: none; "
            f"border-radius: 11px; padding: 10px 22px; font-size: 13px; font-weight: 700; }}"
            f"QPushButton:hover {{ background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            f"stop:0 {h1},stop:1 {h2}); }}"
            f"QPushButton:pressed {{ opacity: 0.85; }}"
        )
        return btn

    def _cancel_btn(self, text="Отмена"):
        t = theme.current
        btn = QPushButton(text)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet(
            f"QPushButton {{ background: rgba(255,255,255,0.06); color: {t['TEXT_SEC']}; "
            f"border: 1px solid {t['BORDER']}; border-radius: 11px; "
            f"padding: 10px 22px; font-size: 13px; }}"
            f"QPushButton:hover {{ background: rgba(255,255,255,0.10); color: {t['TEXT_PRI']}; }}"
        )
        btn.clicked.connect(self.reject)
        return btn


class AddConfigDialog(_BaseDialog):
    """Frameless rounded provider dialog."""

    def __init__(self, parent=None):
        super().__init__(parent, width=520, height=270)
        t = theme.current

        # Icon + title row
        title_row = QHBoxLayout()
        title_row.setSpacing(12)
        icon_lbl = QLabel("🔗")
        icon_lbl.setStyleSheet(
            f"font-size: 22px; background: {hex_rgba(t['ACCENT'], 0.14)}; "
            f"border-radius: 12px; padding: 6px 10px;"
        )
        title_lbl = QLabel("Добавить провайдера")
        title_lbl.setStyleSheet(f"color: {t['TEXT_PRI']}; font-size: 17px; font-weight: 800;")
        title_row.addWidget(icon_lbl)
        title_row.addWidget(title_lbl)
        title_row.addStretch()
        self.fl.addLayout(title_row)

        desc = QLabel(
            "Вставьте ссылку VLESS / VMESS / TROJAN / Shadowsocks\n"
            "или HTTPS-ссылку на подписку."
        )
        desc.setStyleSheet(f"color: {t['TEXT_SEC']}; font-size: 12px; line-height: 1.5;")
        self.fl.addWidget(desc)

        self.url_input = QLineEdit()
        self._paste_from_clipboard(initial=True)
        self.url_input.setPlaceholderText("vless://…  или  https://subscribe.example/…")
        self.url_input.setStyleSheet(
            f"QLineEdit {{ background: {t['MENU_BG']}; color: {t['TEXT_PRI']}; "
            f"border: 1.5px solid {t['BORDER']}; border-radius: 11px; "
            f"padding: 11px 14px; font-size: 13px; }}"
            f"QLineEdit:focus {{ border: 1.5px solid {t['ACCENT']}; "
            f"background: {hex_rgba(t['ACCENT'], 0.04)}; }}"
        )
        self.fl.addWidget(self.url_input)

        row = QHBoxLayout()
        row.setSpacing(10)

        btn_paste = QPushButton("⎘  Вставить")
        btn_paste.setCursor(Qt.PointingHandCursor)
        btn_paste.setStyleSheet(ghost_btn_qss(padding="9px 14px", font_size=12))
        btn_paste.clicked.connect(self._paste_from_clipboard)
        row.addWidget(btn_paste)
        row.addStretch()

        row.addWidget(self._cancel_btn())
        add_btn = self._accent_btn("Добавить")
        add_btn.clicked.connect(self.accept)
        row.addWidget(add_btn)
        self.fl.addLayout(row)

    def _paste_from_clipboard(self, initial=False):
        text = QApplication.clipboard().text().strip()
        if text and (initial or self.url_input.text().strip() == ""):
            ok = text.split("://")[0].lower() in (
                "vless", "vmess", "trojan", "ss", "http", "https"
            )
            if ok:
                self.url_input.setText(text)
                self.url_input.setFocus()

    def get_config_url(self):
        return self.url_input.text().strip()

    def set_config_url(self, text):
        self.url_input.setText(text)
        self.url_input.setFocus()


class ConfirmDialog(_BaseDialog):
    """Generic yes/no confirmation dialog with icon."""

    def __init__(self, title, message, confirm_text="Подтвердить",
                 confirm_color=None, icon="⚠️", parent=None):
        super().__init__(parent, width=460, height=230)
        t = theme.current

        title_row = QHBoxLayout()
        title_row.setSpacing(12)
        icon_lbl = QLabel(icon)
        icon_lbl.setStyleSheet(
            f"font-size: 22px; background: {hex_rgba(t['YELLOW'], 0.14)}; "
            f"border-radius: 12px; padding: 6px 10px;"
        )
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(f"color: {t['TEXT_PRI']}; font-size: 16px; font-weight: 800;")
        title_row.addWidget(icon_lbl)
        title_row.addWidget(title_lbl)
        title_row.addStretch()
        self.fl.addLayout(title_row)

        msg_lbl = QLabel(message)
        msg_lbl.setWordWrap(True)
        msg_lbl.setStyleSheet(f"color: {t['TEXT_SEC']}; font-size: 12.5px; line-height: 1.5;")
        self.fl.addWidget(msg_lbl)

        self.fl.addStretch()

        row = QHBoxLayout()
        row.setSpacing(10)
        row.addStretch()
        row.addWidget(self._cancel_btn())

        color = confirm_color or t["ACCENT"]
        acc = QColor(color)
        h1 = acc.lighter(112).name()
        h2 = acc.lighter(128).name()
        ok_btn = QPushButton(confirm_text)
        ok_btn.setCursor(Qt.PointingHandCursor)
        ok_btn.setStyleSheet(
            f"QPushButton {{ background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            f"stop:0 {color},stop:1 {h1}); color: white; border: none; "
            f"border-radius: 11px; padding: 10px 22px; font-size: 13px; font-weight: 700; }}"
            f"QPushButton:hover {{ background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            f"stop:0 {h1},stop:1 {h2}); }}"
        )
        ok_btn.clicked.connect(self.accept)
        row.addWidget(ok_btn)
        self.fl.addLayout(row)


class NodeDetailDialog(_BaseDialog):
    """Shows node details in a clean popup."""

    def __init__(self, node, parent=None):
        super().__init__(parent, width=480, height=320)
        t = theme.current

        flag = node.get("_flag", "🌐")
        country = node.get("_country", "")
        name = node.get("ps") or node.get("name") or country or node.get("host", "?")

        # Header
        title_row = QHBoxLayout()
        title_row.setSpacing(12)
        flag_lbl = QLabel(flag)
        flag_lbl.setStyleSheet("font-size: 28px;")
        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        name_lbl = QLabel(name)
        name_lbl.setStyleSheet(f"color: {t['TEXT_PRI']}; font-size: 16px; font-weight: 800;")
        country_lbl = QLabel(country)
        country_lbl.setStyleSheet(f"color: {t['TEXT_DIM']}; font-size: 11px;")
        title_col.addWidget(name_lbl)
        title_col.addWidget(country_lbl)
        title_row.addWidget(flag_lbl)
        title_row.addLayout(title_col)
        title_row.addStretch()
        self.fl.addLayout(title_row)

        # Divider
        div = QFrame()
        div.setFixedHeight(1)
        div.setStyleSheet(f"background: {t['BORDER']};")
        self.fl.addWidget(div)

        # Details grid
        details = [
            ("Хост", node.get("host", "—")),
            ("Порт", str(node.get("port", "—"))),
            ("Протокол", node.get("type", "—").upper()),
            ("Транспорт", node.get("network", "—")),
            ("Безопасность", node.get("security", "—")),
        ]
        lat = node.get("_latency")
        if lat is not None:
            lat_str = f"{lat} ms" if lat >= 0 else "Таймаут"
            details.append(("Задержка", lat_str))

        for label, value in details:
            row = QHBoxLayout()
            row.setContentsMargins(0, 0, 0, 0)
            lbl = QLabel(label)
            lbl.setFixedWidth(100)
            lbl.setStyleSheet(f"color: {t['TEXT_DIM']}; font-size: 11px;")
            val = QLabel(value)
            val.setStyleSheet(f"color: {t['TEXT_PRI']}; font-size: 12px; font-weight: 600;")
            row.addWidget(lbl)
            row.addWidget(val)
            row.addStretch()
            self.fl.addLayout(row)

        self.fl.addStretch()

        row = QHBoxLayout()
        row.addStretch()
        close_btn = self._cancel_btn("Закрыть")
        row.addWidget(close_btn)
        self.fl.addLayout(row)


class QRDialog(_BaseDialog):
    def __init__(self, link, host, parent=None):
        super().__init__(parent, width=340, height=420)
        t = theme.current

        title_row = QHBoxLayout()
        icon_lbl = QLabel("📱")
        icon_lbl.setStyleSheet(
            f"font-size: 20px; background: {hex_rgba(t['ACCENT'], 0.14)}; "
            f"border-radius: 10px; padding: 5px 9px;"
        )
        title_lbl = QLabel(f"Поделиться: {host}")
        title_lbl.setStyleSheet(f"color: {t['TEXT_PRI']}; font-size: 14px; font-weight: 800;")
        title_row.addWidget(icon_lbl)
        title_row.addWidget(title_lbl, 1)
        self.fl.addLayout(title_row)

        try:
            import qrcode
            qr = qrcode.make(link, box_size=6)
            buf = io.BytesIO()
            qr.save(buf, format="PNG")
            buf.seek(0)
            pixmap = QPixmap()
            pixmap.loadFromData(buf.read())
            qr_label = QLabel()
            qr_label.setPixmap(pixmap)
            qr_label.setAlignment(Qt.AlignCenter)
            qr_label.setFixedSize(270, 270)
            qr_label.setStyleSheet(
                f"background: white; border-radius: 12px; padding: 8px;"
            )
            self.fl.addWidget(qr_label, alignment=Qt.AlignCenter)
        except ImportError:
            err = QLabel("Установите пакет qrcode\npip install qrcode[pil]")
            err.setAlignment(Qt.AlignCenter)
            err.setStyleSheet(f"color: {t['TEXT_DIM']}; font-size: 11px;")
            self.fl.addWidget(err)

        row = QHBoxLayout()
        row.setSpacing(10)

        copy_btn = QPushButton("⎘  Копировать ссылку")
        copy_btn.setCursor(Qt.PointingHandCursor)
        copy_btn.setStyleSheet(ghost_btn_qss(padding="9px 14px", font_size=11))
        copy_btn.clicked.connect(lambda: (
            QApplication.clipboard().setText(link),
            self._show_copied(copy_btn)
        ))
        row.addWidget(copy_btn)
        row.addStretch()

        close_btn = self._cancel_btn("Закрыть")
        row.addWidget(close_btn)
        self.fl.addLayout(row)

    def _show_copied(self, btn):
        btn.setText("✓  Скопировано")
        QTimer.singleShot(1500, lambda: btn.setText("⎘  Копировать ссылку"))
