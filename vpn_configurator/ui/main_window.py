import math
import os
import time
import tempfile
import socket
import urllib.request
import subprocess
import json
from collections import deque
from urllib.parse import urlparse as parse_url

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton, QDialog,
    QScrollArea, QFrame, QStackedWidget, QComboBox, QLineEdit,
    QGraphicsOpacityEffect, QGraphicsDropShadowEffect,
    QPlainTextEdit, QButtonGroup, QMenu, QSystemTrayIcon, QFileDialog,
    QApplication,
)
from PySide6.QtCore import QThread, Signal
from PySide6.QtCore import Qt, QRectF, QThread, Signal, QTimer, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import (
    QPainter, QColor, QRadialGradient, QLinearGradient, QPainterPath, QPen,
    QIcon, QPixmap, QFont, QAction, QShortcut, QKeySequence,
)

from vpn_configurator.ui import theme
from vpn_configurator.ui.theme import GLOBAL_QSS, card_qss, ghost_btn_qss, hex_rgba
from vpn_configurator.ui.components.graph import TrafficGraph
from vpn_configurator.ui.components.connect_button import ConnectButton, ConnectState
from vpn_configurator.ui.components.switch import SwitchToggle
from vpn_configurator.ui.components.modals import AddConfigDialog, QRDialog
from vpn_configurator.ui.components.toast import Toast
from vpn_configurator.core.config_parser import parse_config, parse_subscription_all
from vpn_configurator.core.xray_manager import XRayThread
from vpn_configurator.core.stats import TrafficStats, SpeedTestThread
from vpn_configurator.core.healthcheck import HealthCheckThread
from vpn_configurator.core.storage import load_data, save_data
from vpn_configurator.core import storage
from vpn_configurator.core.geo import detect_country
from vpn_configurator.core.sysproxy import set_system_proxy
from vpn_configurator.core.firewall import killswitch_enable, killswitch_disable, _is_admin
from vpn_configurator.core.logger import log as file_log
from vpn_configurator.core.sub_fetcher import SubFetchThread
from vpn_configurator.core.split_tunnel import load_split_apps, save_split_apps, get_running_processes
from vpn_configurator.core.dns_override import load_dns_config, save_dns_config, PRESET_DNS, get_preset_dns_list
from vpn_configurator.core.ipv6_support import load_ipv6_config, save_ipv6_config
from vpn_configurator.core.xray_updater import load_update_config, save_update_config, check_for_updates, download_xray_update
from vpn_configurator.core.app_killswitch import load_killswitch_apps, save_killswitch_apps


class UpdateCheckThread(QThread):
    result = Signal(dict)

    def run(self):
        result = check_for_updates()
        self.result.emit(result or {})

BG = ""
ACCENT = ""
ACCENT_LIGHT = ""
CARD = ""
CARD_HOVER = ""
CARD_ACTIVE = ""
BORDER = ""
BORDER_HOVER = ""
TEXT_PRI = ""
TEXT_SEC = ""
TEXT_DIM = ""
GREEN = ""
YELLOW = ""
RED = ""
CYAN = ""
GRAD_ACCENT = ""
GRAD_CONNECT = ""
GRAD_DISCONNECT = ""


def _bind_theme_globals():
    global BG, ACCENT, ACCENT_LIGHT, CARD, CARD_HOVER, CARD_ACTIVE, BORDER
    global BORDER_HOVER, TEXT_PRI, TEXT_SEC, TEXT_DIM
    global GREEN, YELLOW, RED, CYAN, GRAD_ACCENT, GRAD_CONNECT, GRAD_DISCONNECT
    t = theme.current
    BG = t["BG"]
    ACCENT = t["ACCENT"]
    ACCENT_LIGHT = t["ACCENT_LIGHT"]
    CARD = t["CARD"]
    CARD_HOVER = t["CARD_HOVER"]
    CARD_ACTIVE = t["CARD_ACTIVE"]
    BORDER = t["BORDER"]
    BORDER_HOVER = t["BORDER_HOVER"]
    TEXT_PRI = t["TEXT_PRI"]
    TEXT_SEC = t["TEXT_SEC"]
    TEXT_DIM = t["TEXT_DIM"]
    GREEN = t["GREEN"]
    YELLOW = t["YELLOW"]
    RED = t["RED"]
    CYAN = t["CYAN"]
    GRAD_ACCENT = t["GRAD_ACCENT"]
    GRAD_CONNECT = t["GRAD_CONNECT"]
    GRAD_DISCONNECT = t["GRAD_DISCONNECT"]


_bind_theme_globals()


class LatencyTestThread(QThread):
    result = Signal(str, int, int)

    def __init__(self, host, port=443, use_proxy=True):
        super().__init__()
        self.host = host
        self.port = port
        self.use_proxy = use_proxy

    def run(self):
        start = time.time()
        try:
            # Always test directly - don't use proxy for latency testing
            # Proxy may not be running yet or may not support the connection
            sock = socket.create_connection((self.host, self.port), timeout=3)
            sock.close()
            ms = int((time.time() - start) * 1000)
            self.result.emit(self.host, self.port, ms)
        except Exception:
            self.result.emit(self.host, self.port, -1)


class TitleBar(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.setObjectName("titleBar")
        self.setFixedHeight(44)
        self._drag_pos = None

        layout = QHBoxLayout()
        layout.setContentsMargins(16, 0, 10, 0)
        layout.setSpacing(6)

        self.logo = QLabel(
            '<span style="color:#FFFFFF; font-size:14px; font-weight:800;">Zify </span>'
            f'<span style="color:{ACCENT_LIGHT}; font-size:14px; font-weight:800;">client</span>'
        )
        layout.addWidget(self.logo)
        layout.addStretch()

        self.min_btn = QPushButton("\u2014")
        self.max_btn = QPushButton("\u25A1")
        self.close_btn = QPushButton("\u2715")

        for btn in (self.min_btn, self.max_btn, self.close_btn):
            btn.setFixedSize(42, 28)

        self.min_btn.clicked.connect(lambda: self.window().showMinimized())
        self.max_btn.clicked.connect(self._toggle_max)
        self.close_btn.clicked.connect(lambda: self.window().close())

        layout.addWidget(self.min_btn)
        layout.addWidget(self.max_btn)
        layout.addWidget(self.close_btn)
        self.setLayout(layout)
        self.apply_theme()

    def _toggle_max(self):
        w = self.window()
        if w.isMaximized():
            w.showNormal()
        else:
            w.showMaximized()

    def apply_theme(self):
        self.logo.setText(
            '<span style="color:#FFFFFF; font-size:14px; font-weight:800;">Zify </span>'
            f'<span style="color:{ACCENT_LIGHT}; font-size:14px; font-weight:800;">client</span>'
        )
        win_style = (
            f"QPushButton {{ background: transparent; color: {TEXT_SEC}; border: none; "
            f"font-size: 14px; padding: 4px 10px; border-radius: 7px; }}"
            f"QPushButton:hover {{ background: rgba(255,255,255,0.07); color: white; }}"
        )
        close_style = (
            "QPushButton { background: transparent; color: #9AA3B8; border: none; "
            "font-size: 14px; padding: 4px 10px; border-radius: 7px; }"
            "QPushButton:hover { background: #E5484D; color: white; }"
        )
        for btn, st in [
            (self.min_btn, win_style),
            (self.max_btn, win_style),
            (self.close_btn, close_style),
        ]:
            btn.setStyleSheet(st)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPosition().toPoint()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self._drag_pos is not None:
            delta = event.globalPosition().toPoint() - self._drag_pos
            w = self.window()
            w.move(w.x() + delta.x(), w.y() + delta.y())
            self._drag_pos = event.globalPosition().toPoint()
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = None
            event.accept()


class PickRow(QFrame):
    clicked = Signal(int, int)

    def __init__(self, pi, ni, parent=None):
        super().__init__(parent)
        self.pi = pi
        self.ni = ni
        self.setCursor(Qt.PointingHandCursor)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.pi, self.ni)
        super().mousePressEvent(event)


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        stored = load_data()
        theme.apply(((stored.get("settings") or {}).get("theme")) or theme.DEFAULT_NAME)
        _bind_theme_globals()

        self.config_file = None
        self.stats_thread = None
        self.xray_thread = None
        self.providers = []
        self.selected_provider_index = -1
        self.selected_node_index = -1
        self.session_down = 0.0
        self.session_up = 0.0
        self._latency_threads = []
        self._fastest_results = {}
        self._health_thread = None
        self._last_check_ip = None
        self._health_status = None
        self._provider_folders = {}
        self._lat_labels = {}
        self._lat_labels_pick = {}
        self._settings_values = {}
        self._status_text = "Disconnected"
        self._status_color = RED
        self._metric_status_text = "Disconnected"
        self._metric_status_color = RED
        self._last_latency_ms = None
        self._last_down_text = "0 B/s"
        self._last_up_text = "0 B/s"
        self._traffic_active = False
        self._glow_active = False
        self._glow_phase = 0.0
        self._filter_proto = None
        self._filter_country = None
        self._filter_query = ""
        self._top3 = False
        self._fav_only = False
        self._ping_pending = set()
        self._ping_frame = 0
        self._log_lines = deque(maxlen=500)
        self._quitting = False
        self._sys_proxy_active = False
        self._smart_retries = 0
        self._fast_select_autoconnect = False
        self._routing_domains = []
        self._last_ping_text = "\u2014 ms"
        self._loading_subscriptions = {}
        self._killswitch_active = False
        self._split_apps = []
        self._dns_config = {}
        self._ipv6_config = {}
        self._update_config = {}
        self._killswitch_apps = []

        self.setWindowFlag(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(980, 760)
        self.setWindowTitle("Zify client")
        self.setObjectName("appWindow")
        self.setStyleSheet(GLOBAL_QSS())

        root = QVBoxLayout()
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        self.setLayout(root)
        self.title_bar = TitleBar(self)
        root.addWidget(self.title_bar)

        self.body_layout = QHBoxLayout()
        self.body_layout.setContentsMargins(0, 0, 0, 0)
        self.body_layout.setSpacing(0)
        self.sidebar_widget = self._build_sidebar()
        self.body_layout.addWidget(self.sidebar_widget)
        self.stack = QStackedWidget()
        self.body_layout.addWidget(self.stack, 1)
        root.addLayout(self.body_layout, 1)

        self.page_connection = self._build_connection_page()
        self.page_servers = self._build_servers_page()
        self.page_settings = self._build_settings_page()
        self.page_logs = self._build_logs_page()
        self.stack.addWidget(self.page_connection)
        self.stack.addWidget(self.page_servers)
        self.stack.addWidget(self.page_settings)
        self.stack.addWidget(self.page_logs)

        self.toast = Toast(self)
        self.tray = self._setup_tray()
        self._setup_shortcuts()

        self._ping_spin_timer = QTimer(self)
        self._ping_spin_timer.setInterval(180)
        self._ping_spin_timer.timeout.connect(self._ping_spin_tick)

        self._filter_debounce = QTimer(self)
        self._filter_debounce.setSingleShot(True)
        self._filter_debounce.setInterval(200)
        self._filter_debounce.timeout.connect(self._refresh_server_pick)

        self._glow_timer = QTimer(self)
        self._glow_timer.setInterval(16)
        self._glow_timer.timeout.connect(self._glow_tick)

        self._restore_state()
        self._log_line("Application started")

        self.ping_timer = QTimer(self)
        self.ping_timer.setInterval(5000)
        self.ping_timer.timeout.connect(self._quick_ping)

        self._refresh_timer = QTimer(self)
        self._refresh_timer.setInterval(6 * 60 * 60 * 1000)
        self._refresh_timer.timeout.connect(self._refresh_all_subscriptions)
        self._refresh_timer.start()

    # ---------- window painting ----------

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        if self.isMaximized():
            p.fillRect(self.rect(), QColor(BG))
            p.end()
            return

        radius = 18
        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5), radius, radius)
        p.setClipPath(path)
        p.fillPath(path, QColor(BG))

        phase = self._glow_phase if self._glow_active else 0.0
        a1 = theme.current["GLOW1_ALPHA"]
        a2 = theme.current["GLOW2_ALPHA"]
        if self._glow_active:
            a1 = max(0, a1 + int(3.0 * math.sin(phase)))
            a2 = max(0, a2 + int(2.0 * math.cos(phase * 0.8)))

        g1 = QColor(theme.current["GLOW1"])
        g1.setAlpha(int(a1))
        g1c = QColor(g1)
        g1c.setAlpha(0)
        glow1 = QRadialGradient(self.width() * 0.16, 0, 560)
        glow1.setColorAt(0.0, g1)
        glow1.setColorAt(1.0, g1c)
        p.fillRect(self.rect(), glow1)

        g2 = QColor(theme.current["GLOW2"])
        g2.setAlpha(int(a2))
        g2c = QColor(g2)
        g2c.setAlpha(0)
        glow2 = QRadialGradient(self.width() * 0.94, self.height() * 0.98, 430)
        glow2.setColorAt(0.0, g2)
        glow2.setColorAt(1.0, g2c)
        p.fillRect(self.rect(), glow2)

        p.setClipping(False)
        p.setPen(QPen(QColor(255, 255, 255, 16), 1))
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5), radius, radius)
        p.end()

    def _glow_tick(self):
        self._glow_phase += 0.06
        self.update()

    def _set_glow(self, active):
        if self._glow_active == active:
            return
        self._glow_active = active
        if active:
            self._glow_timer.start()
        else:
            self._glow_timer.stop()
        self.update()

    # ---------- persistence ----------

    def _restore_state(self):
        stored = load_data()
        self._load_providers_from_items(stored.get("providers", []))

        settings = stored.get("settings") or {}
        self._settings_values = settings
        if hasattr(self, "cb_system_proxy"):
            self._apply_settings_values()

        sel_prov = stored.get("selected_provider", -1)
        sel_node = stored.get("selected_node", -1)
        if self.providers:
            if 0 <= sel_prov < len(self.providers):
                self._select_provider(sel_prov, sel_node)
            else:
                self._select_provider(0, 0)
            self._rebuild_providers_ui()
            self._refresh_servers_page()
            self._set_status("Configured", YELLOW)

        if self.config_file:
            if settings.get("smart_connect"):
                QTimer.singleShot(700, lambda: self._fast_select(auto_connect=True))
            elif settings.get("autoconnect"):
                QTimer.singleShot(800, self.toggle_connection)

    def _load_providers_from_items(self, items):
        self.providers = []
        for item in items:
            url = item.get("url", "")
            host = item.get("host", "?")
            if not url:
                continue
            try:
                fd, cfg_path = tempfile.mkstemp(suffix=".json", prefix="vpn_")
                os.close(fd)

                cached_nodes = item.get("nodes") or []
                if cached_nodes:
                    self.providers.append({
                        "host": host,
                        "type": item.get("type", "SUB"),
                        "url": url,
                        "parsed": cached_nodes[0],
                        "nodes": cached_nodes,
                        "config_file": cfg_path,
                    })
                    continue

                parsed = parse_config(url)
                sub_url = parsed.get("subscription_url", "")
                if sub_url:
                    pi = len(self.providers)
                    node = {"host": parsed.get("host", "?"), "port": parsed.get("port", 443),
                            "type": parsed.get("type", "vmess"), "_loading": True}
                    provider = {
                        "host": host,
                        "type": "SUB",
                        "url": url,
                        "parsed": parsed,
                        "nodes": [node],
                        "config_file": cfg_path,
                        "_subscription_url": sub_url,
                    }
                    self.providers.append(provider)

                    fetcher = SubFetchThread(url)
                    fetcher.nodes_ready.connect(
                        lambda nodes, p=pi: self._on_subscription_nodes(p, nodes)
                    )
                    fetcher.error.connect(
                        lambda err, p=pi: self._on_subscription_error(p, err)
                    )
                    self._loading_subscriptions[pi] = fetcher
                    fetcher.start()
                else:
                    self.providers.append({
                        "host": host,
                        "type": parsed.get("type", "").upper(),
                        "url": url,
                        "parsed": parsed,
                        "nodes": [parsed],
                        "config_file": cfg_path,
                    })
            except Exception:
                continue

    def _collect_settings(self):
        return {
            "theme": theme.current_name,
            "system_proxy": self.cb_system_proxy.isChecked(),
            "tun_mode": self.cb_tun_mode.isChecked(),
            "autoconnect": self.cb_autoconnect.isChecked(),
            "smart_connect": self.cb_smart_connect.isChecked(),
            "notifications": self.cb_notifications.isChecked(),
            "killswitch": self.cb_killswitch.isChecked(),
            "routing_mode": self.routing_combo.currentData() or "all",
            "routing_domains": list(self._routing_domains),
            "split_tunnel_mode": getattr(self, "split_mode_combo", None).currentData() if hasattr(self, "split_mode_combo") else "exclude",
            "split_tunnel_apps": getattr(self, "_split_apps", []),
            "dns_config": getattr(self, "_dns_config", {}),
            "ipv6_config": getattr(self, "_ipv6_config", {}),
            "update_config": getattr(self, "_update_config", {}),
            "killswitch_apps": getattr(self, "_killswitch_apps", []),
        }

    def _save_state(self):
        settings = self._collect_settings()
        self._settings_values = settings
        save_data(self.providers, self.selected_provider_index, self.selected_node_index, settings)

    def _apply_settings_values(self):
        s = self._settings_values
        self.cb_system_proxy.setChecked(bool(s.get("system_proxy", False)))
        self.cb_tun_mode.setChecked(bool(s.get("tun_mode", False)))
        self.cb_autoconnect.setChecked(bool(s.get("autoconnect", False)))
        self.cb_smart_connect.setChecked(bool(s.get("smart_connect", False)))
        self.cb_notifications.setChecked(bool(s.get("notifications", True)))
        self.cb_killswitch.setChecked(bool(s.get("killswitch", False)))
        mode = s.get("routing_mode", "all")
        idx = self.routing_combo.findData(mode)
        self.routing_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self._routing_domains = list(s.get("routing_domains") or [])
        self._rebuild_routing_domains()
        
        # Load split tunnel apps
        self._split_apps = list(s.get("split_tunnel_apps", []))
        if hasattr(self, "split_mode_combo"):
            split_mode = s.get("split_tunnel_mode", "exclude")
            idx = self.split_mode_combo.findData(split_mode)
            self.split_mode_combo.setCurrentIndex(idx if idx >= 0 else 0)
        if hasattr(self, "split_apps_list"):
            self._rebuild_split_apps()
        
        # Load DNS config
        self._dns_config = s.get("dns_config", {})
        if hasattr(self, "dns_combo"):
            dns_id = self._dns_config.get("dns", "system")
            idx = self.dns_combo.findData(dns_id)
            self.dns_combo.setCurrentIndex(idx if idx >= 0 else 0)
        if hasattr(self, "cb_block_ads"):
            self.cb_block_ads.setChecked(self._dns_config.get("block_ads", False))
        if hasattr(self, "cb_block_trackers"):
            self.cb_block_trackers.setChecked(self._dns_config.get("block_trackers", False))
        if hasattr(self, "cb_block_malware"):
            self.cb_block_malware.setChecked(self._dns_config.get("block_malware", False))
        if hasattr(self, "custom_dns_input"):
            self.custom_dns_input.setText(self._dns_config.get("custom_dns", ""))
        
        # Load IPv6 config
        self._ipv6_config = s.get("ipv6_config", {})
        if hasattr(self, "cb_ipv6_enabled"):
            self.cb_ipv6_enabled.setChecked(self._ipv6_config.get("enabled", True))
        if hasattr(self, "cb_ipv6_dns"):
            self.cb_ipv6_dns.setChecked(self._ipv6_config.get("dns_v6", True))
        if hasattr(self, "cb_ipv6_routing"):
            self.cb_ipv6_routing.setChecked(self._ipv6_config.get("routing_v6", True))
        if hasattr(self, "cb_ipv6_prefer"):
            self.cb_ipv6_prefer.setChecked(self._ipv6_config.get("prefer_v6", False))
        
        # Load update config
        self._update_config = s.get("update_config", {})
        if hasattr(self, "cb_auto_update"):
            self.cb_auto_update.setChecked(self._update_config.get("auto_update", False))
        
        # Load killswitch apps
        self._killswitch_apps = list(s.get("killswitch_apps", []))
        if hasattr(self, "killswitch_apps_list"):
            self._rebuild_killswitch_apps()

    # ---------- sidebar ----------

    def _build_sidebar(self):
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(212)
        sidebar.setStyleSheet(
            f"QWidget#sidebar {{ background: rgba(255,255,255,0.02); "
            f"border-right: 1px solid {BORDER}; }}"
        )
        layout = QVBoxLayout()
        layout.setContentsMargins(14, 22, 14, 16)
        layout.setSpacing(4)
        sidebar.setLayout(layout)

        logo = QLabel(
            '<span style="color:#FFFFFF; font-size:18px; font-weight:800;">Zify</span> '
            f'<span style="color:{ACCENT_LIGHT}; font-size:18px; font-weight:800;">client</span>'
        )
        layout.addWidget(logo)
        layout.addSpacing(12)

        status_row = QHBoxLayout()
        status_row.setContentsMargins(4, 0, 4, 0)
        status_row.setSpacing(8)
        self.side_dot = QLabel("\u25CF")
        self.side_dot.setStyleSheet(f"color: {RED}; font-size: 9px;")
        self.side_status = QLabel("Disconnected")
        self.side_status.setStyleSheet(f"color: {RED}; font-size: 11px; font-weight: 600;")
        status_row.addWidget(self.side_dot)
        status_row.addWidget(self.side_status)
        status_row.addStretch()
        layout.addLayout(status_row)
        layout.addSpacing(10)

        self.nav_btns = []
        self.nav_markers = []
        nav_targets = [
            ("🔌  Connection", 0),
            ("🖥  Servers", 1),
            ("⚙️  Settings", 2),
            ("📋  Logs", 3),
        ]
        for text, idx in nav_targets:
            row = QWidget()
            row_lo = QHBoxLayout()
            row_lo.setContentsMargins(0, 0, 0, 0)
            row_lo.setSpacing(8)
            marker = QLabel()
            marker.setFixedSize(3, 18)
            marker.setStyleSheet("background: transparent; border-radius: 2px;")
            btn = QPushButton(text)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFixedHeight(38)
            btn.clicked.connect(lambda checked, i=idx: self._switch_page(i))
            row_lo.addWidget(marker)
            row_lo.addWidget(btn, 1)
            row.setLayout(row_lo)
            self.nav_markers.append(marker)
            self.nav_btns.append(btn)
            layout.addWidget(row)

        layout.addSpacing(6)
        layout.addStretch()

        ver = QLabel("v4.2 PREMIUM \u00b7 XRAY-CORE")
        ver.setStyleSheet(
            f"color: {TEXT_DIM}; font-size: 8.5px; font-weight: 600; "
            "letter-spacing: 1.2px; padding: 0 4px;"
        )
        layout.addWidget(ver)

        self._set_nav_active(0)
        return sidebar

    def _set_nav_active(self, idx):
        style_idle = (
            "QPushButton { text-align: left; padding: 0 12px; border: none; "
            f"border-radius: 9px; color: {TEXT_SEC}; font-size: 13px; "
            "background: transparent; }"
            f"QPushButton:hover {{ background: rgba(255,255,255,0.05); color: {TEXT_PRI}; }}"
        )
        style_active = (
            "QPushButton { text-align: left; padding: 0 12px; border: none; "
            f"border-radius: 9px; color: #FFFFFF; font-size: 13px; font-weight: 700; "
            f"background: qlineargradient(x1:0, y1:0, x2:1, y2:0, "
            f"stop: 0 {hex_rgba(ACCENT, 0.28)}, stop: 1 {hex_rgba(ACCENT, 0.04)}); }}"
        )
        for i, (btn, marker) in enumerate(zip(self.nav_btns, self.nav_markers)):
            if i == idx:
                btn.setStyleSheet(style_active)
                marker.setStyleSheet(f"background: {ACCENT}; border-radius: 2px;")
            else:
                btn.setStyleSheet(style_idle)
                marker.setStyleSheet("background: transparent; border-radius: 2px;")

    def _switch_page(self, idx):
        cur = self.stack.currentIndex()
        if idx == cur:
            if idx == 1:
                self._refresh_servers_page()
            return

        self._set_nav_active(idx)
        self.stack.setCurrentIndex(idx)
        self._fade_in_widget(self.stack.widget(idx))

    def _fade_in_widget(self, widget):
        prev = widget.graphicsEffect()
        if prev is not None:
            widget.setGraphicsEffect(None)
        eff = QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(eff)
        eff.setOpacity(0.0)
        fade = QPropertyAnimation(eff, b"opacity", self)
        fade.setDuration(240)
        fade.setStartValue(0.0)
        fade.setEndValue(1.0)
        fade.setEasingCurve(QEasingCurve.OutCubic)
        fade.finished.connect(lambda: self._clear_effect(widget, eff))
        fade.start(QPropertyAnimation.DeleteWhenStopped)

    def _clear_effect(self, widget, effect):
        try:
            if widget.graphicsEffect() is effect:
                widget.setGraphicsEffect(None)
        except RuntimeError:
            pass

    # ---------- status helpers ----------

    def _set_status(self, text, color):
        self._status_text = text
        self._status_color = color
        self.side_dot.setStyleSheet(f"color: {color}; font-size: 9px;")
        self.side_status.setText(text)
        self.side_status.setStyleSheet(f"color: {color}; font-size: 11px; font-weight: 600;")
        self._update_tray()

    def _set_metric_status(self, text, color):
        self._metric_status_text = text
        self._metric_status_color = color
        self.metric_status.setText(text)
        self.metric_status.setStyleSheet(
            f"color: {color}; font-size: 15px; font-weight: bold;"
        )

    # ---------- connection page ----------

    def _build_connection_page(self):
        page = QWidget()
        page.setObjectName("pageConnection")
        cl = QVBoxLayout()
        cl.setContentsMargins(20, 14, 20, 14)
        cl.setSpacing(10)
        page.setLayout(cl)

        cl.addWidget(self._build_metrics_bar())
        cl.addWidget(self._build_network_card(), 1)
        cl.addWidget(self._build_connect_section())
        cl.addWidget(self._build_traffic_section())

        return page

    @staticmethod
    def _elevate(widget, blur=26, y=6, alpha=95):
        shadow = QGraphicsDropShadowEffect(widget)
        shadow.setBlurRadius(blur)
        shadow.setOffset(0, y)
        shadow.setColor(QColor(0, 0, 0, alpha))
        widget.setGraphicsEffect(shadow)

    def _build_metrics_bar(self):
        bar = QWidget()
        bar.setObjectName("card_metrics")
        bar.setFixedHeight(60)
        bar.setStyleSheet(card_qss("#card_metrics", radius=16, hover=False))
        self._elevate(bar, blur=24, y=5)
        layout = QHBoxLayout()
        layout.setContentsMargins(18, 0, 18, 0)
        layout.setSpacing(0)
        bar.setLayout(layout)

        items = [
            ("LATENCY", self._metric_widget("LATENCY", "-- ms")),
            ("DOWNLOAD", self._metric_widget("DOWNLOAD", "0 B/s")),
            ("UPLOAD", self._metric_widget("UPLOAD", "0 B/s")),
            ("STATUS", self._metric_widget("STATUS", "Disconnected")),
            ("SERVER", self._metric_widget("SERVER", "None")),
        ]
        for i, (key, w) in enumerate(items):
            layout.addWidget(w, 1)
            if i != len(items) - 1:
                sep = QFrame()
                sep.setFixedWidth(1)
                sep.setFixedHeight(30)
                sep.setStyleSheet(f"background: {BORDER};")
                layout.addWidget(sep)
        return bar

    def _metric_widget(self, title, value):
        w = QWidget()
        lo = QVBoxLayout()
        lo.setContentsMargins(8, 6, 8, 6)
        lo.setSpacing(2)
        w.setLayout(lo)

        lbl_title = QLabel(title)
        lbl_title.setStyleSheet(
            f"color: {TEXT_DIM}; font-size: 8.5px; font-weight: 700; letter-spacing: 2px;"
        )
        lbl_title.setAlignment(Qt.AlignCenter)

        if title == "LATENCY":
            self.metric_latency = QLabel(value)
            self.metric_latency.setStyleSheet(f"color: {TEXT_SEC}; font-size: 15px; font-weight: bold;")
            self.metric_latency.setAlignment(Qt.AlignCenter)
            lo.addWidget(lbl_title)
            lo.addWidget(self.metric_latency)
        elif title == "DOWNLOAD":
            self.metric_down = QLabel(value)
            self.metric_down.setStyleSheet(f"color: {CYAN}; font-size: 15px; font-weight: bold;")
            self.metric_down.setAlignment(Qt.AlignCenter)
            lo.addWidget(lbl_title)
            lo.addWidget(self.metric_down)
        elif title == "UPLOAD":
            self.metric_up = QLabel(value)
            self.metric_up.setStyleSheet(f"color: {RED}; font-size: 15px; font-weight: bold;")
            self.metric_up.setAlignment(Qt.AlignCenter)
            lo.addWidget(lbl_title)
            lo.addWidget(self.metric_up)
        elif title == "STATUS":
            self.metric_status = QLabel(value)
            self.metric_status.setStyleSheet(f"color: {RED}; font-size: 15px; font-weight: bold;")
            self.metric_status.setAlignment(Qt.AlignCenter)
            lo.addWidget(lbl_title)
            lo.addWidget(self.metric_status)
        elif title == "SERVER":
            self.metric_server = QLabel(value)
            self.metric_server.setStyleSheet(f"color: {TEXT_PRI}; font-size: 12px; font-weight: bold;")
            self.metric_server.setAlignment(Qt.AlignCenter)
            lo.addWidget(lbl_title)
            lo.addWidget(self.metric_server)
        return w

    def _build_network_card(self):
        card = QWidget()
        card.setObjectName("card_network")
        card.setMinimumHeight(0)
        card.setStyleSheet(card_qss("#card_network", radius=16))
        self._elevate(card, blur=30, y=8)
        layout = QVBoxLayout()
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(12)
        card.setLayout(layout)

        header_row = QHBoxLayout()
        header_row.setSpacing(10)

        header_col = QVBoxLayout()
        header_col.setSpacing(1)
        header = QLabel("Network")
        header.setStyleSheet(f"color: {TEXT_PRI}; font-size: 14px; font-weight: 800;")
        self.network_hint = QLabel("no provider selected")
        self.network_hint.setStyleSheet(f"color: {TEXT_DIM}; font-size: 10px;")
        header_col.addWidget(header)
        header_col.addWidget(self.network_hint)
        header_row.addLayout(header_col)
        header_row.addStretch()

        self.btn_fast_select = QPushButton("\u26A1  Быстрый выбор")
        self.btn_fast_select.setCursor(Qt.PointingHandCursor)
        self.btn_fast_select.setStyleSheet(ghost_btn_qss(color=GREEN, radius=8, padding="4px 10px", font_size=10))
        self.btn_fast_select.setToolTip("Измерить задержку всех серверов и выбрать лучший")
        self.btn_fast_select.clicked.connect(self._fast_select)
        header_row.addWidget(self.btn_fast_select)

        self.btn_ping_all = QPushButton("Пинг")
        self.btn_ping_all.setCursor(Qt.PointingHandCursor)
        self.btn_ping_all.setStyleSheet(ghost_btn_qss(radius=8, padding="4px 10px", font_size=10))
        self.btn_ping_all.clicked.connect(self._ping_all_servers)
        header_row.addWidget(self.btn_ping_all)

        btn_add = QPushButton("+  Добавить")
        btn_add.setCursor(Qt.PointingHandCursor)
        btn_add.setStyleSheet(ghost_btn_qss(color=ACCENT, radius=8, padding="4px 10px", font_size=10))
        btn_add.clicked.connect(self.show_add_config_dialog)
        header_row.addWidget(btn_add)

        layout.addLayout(header_row)

        self.providers_scroll = QScrollArea()
        self.providers_scroll.setWidgetResizable(True)
        self.providers_scroll.setFixedHeight(68)
        self.providers_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.providers_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.providers_inner = QWidget()
        self.providers_chips_layout = QHBoxLayout()
        self.providers_chips_layout.setContentsMargins(0, 0, 0, 0)
        self.providers_chips_layout.setSpacing(8)
        self.providers_inner.setLayout(self.providers_chips_layout)
        self.providers_scroll.setWidget(self.providers_inner)
        layout.addWidget(self.providers_scroll)

        divider = QFrame()
        divider.setFixedHeight(1)
        divider.setStyleSheet(f"background: {BORDER};")
        layout.addWidget(divider)

        layout.addWidget(self._build_filter_bar())

        self.pick_scroll = QScrollArea()
        self.pick_scroll.setWidgetResizable(True)
        self.pick_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.pick_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.pick_container = QWidget()
        self.pick_layout = QVBoxLayout()
        self.pick_layout.setContentsMargins(0, 0, 0, 0)
        self.pick_layout.setSpacing(6)
        self.pick_container.setLayout(self.pick_layout)
        self.pick_scroll.setWidget(self.pick_container)
        layout.addWidget(self.pick_scroll, 1)

        self.pick_empty = QLabel("Select a provider to see its nodes")
        self.pick_empty.setStyleSheet(f"color: {TEXT_DIM}; font-size: 11px;")
        self.pick_empty.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.pick_empty)

        self._refresh_server_pick()
        return card

    def _rebuild_providers_ui(self):
        while self.providers_chips_layout.count():
            item = self.providers_chips_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        for idx, prov in enumerate(self.providers):
            is_sel = idx == self.selected_provider_index
            nodes = prov.get("nodes", [])
            n_nodes = len(nodes)

            # Pick best flag from nodes
            flag = "\U0001F310"
            for n in nodes:
                f = n.get("_flag")
                if f and f != "\U0001F310":
                    flag = f
                    break

            card = QPushButton()
            card.setFixedSize(110, 64)
            card.setCursor(Qt.PointingHandCursor)
            if is_sel:
                card.setStyleSheet(
                    f"QPushButton {{ background: {CARD_ACTIVE}; border: 1.5px solid {ACCENT}; "
                    f"border-radius: 14px; }}"
                    f"QPushButton:hover {{ border: 1.5px solid {ACCENT_LIGHT}; }}"
                )
            else:
                card.setStyleSheet(
                    f"QPushButton {{ background: rgba(255,255,255,0.03); "
                    f"border: 1px solid {BORDER}; border-radius: 14px; }}"
                    f"QPushButton:hover {{ background: {CARD_HOVER}; "
                    f"border: 1px solid {BORDER_HOVER}; }}"
                )
            clo = QVBoxLayout()
            clo.setContentsMargins(10, 8, 10, 8)
            clo.setSpacing(2)
            card.setLayout(clo)

            flag_lbl = QLabel(flag)
            flag_lbl.setStyleSheet("font-size: 20px; background: transparent; border: none;")
            flag_lbl.setAlignment(Qt.AlignLeft)
            clo.addWidget(flag_lbl)

            host_lbl = QLabel(prov.get("host", "Unknown"))
            host_lbl.setStyleSheet(
                f"color: {TEXT_PRI}; font-size: 10px; font-weight: 700; "
                "background: transparent; border: none;"
            )
            host_lbl.setWordWrap(False)
            clo.addWidget(host_lbl)

            count_lbl = QLabel(f"{n_nodes} серверов" if n_nodes != 1 else "1 сервер")
            count_lbl.setStyleSheet(
                f"color: {TEXT_DIM}; font-size: 8px; font-weight: 500; "
                "background: transparent; border: none;"
            )
            clo.addWidget(count_lbl)

            card.clicked.connect(lambda checked, i=idx: self._select_provider(i, 0))
            self.providers_chips_layout.addWidget(card)

        add_btn = QPushButton()
        add_btn.setFixedSize(64, 64)
        add_btn.setCursor(Qt.PointingHandCursor)
        add_btn.setStyleSheet(
            f"QPushButton {{ background: transparent; border: 1px dashed {BORDER_HOVER}; "
            f"color: {TEXT_SEC}; font-size: 22px; border-radius: 14px; }}"
            f"QPushButton:hover {{ border-color: {ACCENT}; color: {ACCENT_LIGHT}; }}"
        )
        add_btn.setText("+")
        add_btn.setToolTip("Добавить провайдера")
        add_btn.clicked.connect(self.show_add_config_dialog)
        self.providers_chips_layout.addWidget(add_btn)
        self.providers_chips_layout.addStretch()

    # ---------- node filters ----------

    def _chip_qss(self):
        return (
            "QPushButton { background: transparent; color: " + TEXT_SEC + "; "
            f"border: 1px solid {BORDER}; border-radius: 7px; padding: 3px 9px; "
            "font-size: 9.5px; font-weight: 600; }"
            f"QPushButton:hover {{ color: {TEXT_PRI}; border-color: {BORDER_HOVER}; }}"
            f"QPushButton:checked {{ background: {hex_rgba(ACCENT, 0.18)}; "
            f"color: {ACCENT_LIGHT}; border-color: {hex_rgba(ACCENT, 0.6)}; }}"
        )

    def _fav_btn_qss(self, active):
        color = "#FFD54A" if active else TEXT_DIM
        return (
            f"QPushButton {{ background: {'rgba(255,213,74,0.12)' if active else 'transparent'}; "
            f"color: {color}; border: none; border-radius: 13px; font-size: 14px; }}"
            f"QPushButton:hover {{ background: rgba(255,213,74,0.18); color: #FFD54A; }}"
        )

    def _build_filter_bar(self):
        bar = QWidget()
        lo = QHBoxLayout()
        lo.setContentsMargins(0, 0, 0, 0)
        lo.setSpacing(6)
        bar.setLayout(lo)

        self.filter_search = QLineEdit()
        self.filter_search.setPlaceholderText("Search \u2026  (Ctrl+F)")
        self.filter_search.setFixedWidth(148)
        self.filter_search.setStyleSheet(
            f"QLineEdit {{ background: rgba(255,255,255,0.04); border: 1px solid {BORDER}; "
            f"border-radius: 8px; padding: 5px 10px; color: {TEXT_PRI}; font-size: 10.5px; }}"
            f"QLineEdit:focus {{ border: 1px solid {ACCENT}; }}"
        )
        self.filter_search.textChanged.connect(self._on_filter_query)
        lo.addWidget(self.filter_search)

        self.proto_group = QButtonGroup(self)
        self.proto_group.setExclusive(True)
        self._proto_chips = {}
        for key, label in [
            (None, "ALL"), ("vless", "VLESS"), ("vmess", "VMESS"),
            ("trojan", "TROJAN"), ("ss", "SS"),
        ]:
            chip = QPushButton(label)
            chip.setCheckable(True)
            chip.setCursor(Qt.PointingHandCursor)
            chip.setStyleSheet(self._chip_qss())
            chip.setFixedHeight(24)
            self.proto_group.addButton(chip)
            self._proto_chips[key] = chip
            chip.clicked.connect(lambda checked, k=key: self._on_filter_proto(k))
            lo.addWidget(chip)
        active_chip = self._proto_chips.get(self._filter_proto, self._proto_chips[None])
        active_chip.setChecked(True)

        self.country_combo = QComboBox()
        self.country_combo.setFixedWidth(150)
        self.country_combo.currentIndexChanged.connect(self._on_filter_country)
        lo.addWidget(self.country_combo)

        self.btn_top3 = QPushButton("\u26A1 Top 3")
        self.btn_top3.setCheckable(True)
        self.btn_top3.setCursor(Qt.PointingHandCursor)
        self.btn_top3.setStyleSheet(self._chip_qss())
        self.btn_top3.setFixedHeight(24)
        self.btn_top3.setChecked(self._top3)
        self.btn_top3.toggled.connect(self._on_filter_top3)
        lo.addWidget(self.btn_top3)

        self.btn_fav = QPushButton("\u2605 Favorites")
        self.btn_fav.setCheckable(True)
        self.btn_fav.setCursor(Qt.PointingHandCursor)
        self.btn_fav.setStyleSheet(self._chip_qss())
        self.btn_fav.setFixedHeight(24)
        self.btn_fav.setChecked(self._fav_only)
        self.btn_fav.toggled.connect(self._on_filter_fav)
        lo.addWidget(self.btn_fav)
        lo.addStretch()
        return bar

    def _on_filter_proto(self, proto):
        self._filter_proto = proto
        self._refresh_server_pick()

    def _on_filter_country(self):
        self._filter_country = self.country_combo.currentData()
        self._refresh_server_pick()

    def _on_filter_query(self, text):
        self._filter_query = text.strip().lower()
        self._filter_debounce.start()

    def _on_filter_top3(self, checked):
        self._top3 = checked
        self._refresh_server_pick()

    def _on_filter_fav(self, checked):
        self._fav_only = checked
        self._refresh_server_pick()

    def _refresh_country_filter(self):
        if not hasattr(self, "country_combo"):
            return
        current = self.country_combo.currentData()
        countries = set()
        for prov in self.providers:
            for node in prov.get("nodes", []):
                flag, country = node.get("_flag"), node.get("_country")
                if flag is None:
                    flag, country = detect_country(node)
                    if flag is None:
                        flag, country = "\U0001F310", "Unknown"
                    node["_flag"], node["_country"] = flag, country
                countries.add((flag, country))
        self.country_combo.blockSignals(True)
        self.country_combo.clear()
        self.country_combo.addItem("All countries", None)
        for flag, country in sorted(countries, key=lambda x: x[1]):
            self.country_combo.addItem(f"{flag} {country}", country)
        idx = self.country_combo.findData(current)
        self.country_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self.country_combo.blockSignals(False)

    def _visible_node_indices(self, nodes):
        result = []
        for ni, node in enumerate(nodes):
            if self._filter_proto and node.get("type", "").lower() != self._filter_proto:
                continue
            if self._filter_country:
                flag, country = node.get("_flag"), node.get("_country")
                if flag is None:
                    flag, country = detect_country(node)
                    if flag is None:
                        flag, country = "\U0001F310", "Unknown"
                    node["_flag"], node["_country"] = flag, country
                if country != self._filter_country:
                    continue
            if self._filter_query:
                text = " ".join(str(node.get(k, "")) for k in ("host", "ps", "name")).lower()
                text += " " + str(node.get("_country", "")).lower()
                if self._filter_query not in text:
                    continue
            if self._fav_only and not node.get("_favorite"):
                continue
            result.append(ni)
        if self._top3:
            scored = []
            for ni in result:
                lat = nodes[ni].get("_latency")
                if lat is not None and lat >= 0:
                    scored.append((lat, ni))
            scored.sort()
            result = [ni for _, ni in scored[:3]]
        return result

    def _refresh_server_pick(self):
        for i in reversed(range(self.pick_layout.count())):
            w = self.pick_layout.itemAt(i).widget()
            if w:
                w.deleteLater()
        self._lat_labels_pick = {}

        pi = self.selected_provider_index
        if pi < 0 or pi >= len(self.providers):
            self.network_hint.setText("no provider selected")
            self.pick_empty.setText("Select a provider to see its nodes")
            self.pick_empty.show()
            self.pick_scroll.hide()
            return
        prov = self.providers[pi]
        nodes = prov.get("nodes", [])
        if not nodes:
            self.network_hint.setText("0 nodes")
            self.pick_empty.setText("This provider has no nodes")
            self.pick_empty.show()
            self.pick_scroll.hide()
            return
        self._refresh_country_filter()
        visible = self._visible_node_indices(nodes)
        self.network_hint.setText(f"{len(visible)} of {len(nodes)} node{'s' if len(nodes) != 1 else ''}")
        if not visible:
            self.pick_empty.setText("No nodes match the current filters")
            self.pick_empty.show()
            self.pick_scroll.hide()
            return
        self.pick_empty.hide()
        self.pick_scroll.show()
        for real_ni in visible:
            self.pick_layout.addWidget(self._build_pick_row(pi, real_ni, nodes[real_ni]))
        self.pick_layout.addStretch()

    def _build_pick_row(self, pi, ni, node):
        is_selected = (
            pi == self.selected_provider_index
            and ni == self.selected_node_index
        )
        lat = node.get("_latency")
        flag = node.get("_flag")
        country = node.get("_country")
        if flag is None:
            flag, country = detect_country(node)
            if flag is None:
                flag, country = "\U0001F310", "Неизвестно"
            node["_flag"], node["_country"] = flag, country

        # Display name: ps/name field first, fallback to country
        display_name = node.get("ps") or node.get("name") or country or node.get("host", "?")

        card = PickRow(pi, ni)
        card.setObjectName("pick_row")
        if is_selected:
            card.setStyleSheet(
                f"QFrame#pick_row {{ background: {CARD_ACTIVE}; "
                f"border: 1.5px solid {ACCENT}; border-radius: 14px; }}"
            )
        else:
            card.setStyleSheet(
                f"QFrame#pick_row {{ background: rgba(255,255,255,0.02); "
                f"border: 1px solid {BORDER}; border-radius: 14px; }}"
                f"QFrame#pick_row:hover {{ background: {CARD_HOVER}; "
                f"border: 1px solid {BORDER_HOVER}; }}"
            )
        card.setFixedHeight(56)
        card.clicked.connect(self._pick_node)

        layout = QHBoxLayout()
        layout.setContentsMargins(14, 0, 14, 0)
        layout.setSpacing(12)
        card.setLayout(layout)

        # Big flag
        flag_lbl = QLabel(flag)
        flag_lbl.setStyleSheet("font-size: 22px; background: transparent;")
        flag_lbl.setFixedWidth(32)
        layout.addWidget(flag_lbl)

        # Country name + subtitle
        text_col = QVBoxLayout()
        text_col.setSpacing(1)
        text_col.setContentsMargins(0, 0, 0, 0)

        name_lbl = QLabel(display_name)
        name_lbl.setStyleSheet(
            f"color: {TEXT_PRI}; font-size: 13px; font-weight: 700; background: transparent;"
        )
        text_col.addWidget(name_lbl)

        if node.get("_loading"):
            sub_lbl = QLabel("Загрузка…")
            sub_lbl.setStyleSheet(f"color: {CYAN}; font-size: 10px; background: transparent;")
            text_col.addWidget(sub_lbl)
        else:
            sub_lbl = QLabel(country if country != display_name else "")
            sub_lbl.setStyleSheet(f"color: {TEXT_DIM}; font-size: 10px; background: transparent;")
            text_col.addWidget(sub_lbl)

        layout.addLayout(text_col, 1)

        if node.get("_loading"):
            return card

        # Latency badge
        if lat is not None:
            c = GREEN if lat >= 0 and lat < 100 else (YELLOW if lat >= 0 and lat < 250 else RED)
            lat_text = f"{lat} ms" if lat >= 0 else "—"
            lat_lbl = QLabel(lat_text)
            lat_lbl.setStyleSheet(
                f"color: {c}; font-size: 11px; font-weight: 700; background: transparent;"
            )
        else:
            lat_lbl = QLabel("")
            lat_lbl.setStyleSheet(f"color: {TEXT_DIM}; font-size: 11px; background: transparent;")
        self._lat_labels_pick[(pi, ni)] = lat_lbl
        layout.addWidget(lat_lbl)

        # Selected checkmark or arrow
        if is_selected:
            sel_mark = QLabel("✓")
            sel_mark.setStyleSheet(
                f"color: {ACCENT_LIGHT}; font-size: 15px; font-weight: bold; background: transparent;"
            )
            layout.addWidget(sel_mark)
        else:
            arrow = QLabel("›")
            arrow.setStyleSheet(f"color: {TEXT_DIM}; font-size: 16px; background: transparent;")
            layout.addWidget(arrow)

        return card

    def _on_subscription_nodes(self, pi, nodes):
        self._loading_subscriptions.pop(pi, None)
        if 0 <= pi < len(self.providers):
            prov = self.providers[pi]
            if nodes:
                prov["nodes"] = nodes
                prov["parsed"] = nodes[0]
            else:
                prov["nodes"] = []
            prov.pop("_subscription_url", None)
            if prov.get("nodes"):
                for n in prov["nodes"]:
                    n.pop("_loading", None)
            if pi == self.selected_provider_index:
                self._configure_from_selection()
            self._rebuild_providers_ui()
            self._refresh_servers_page()
            self._save_state()
            count = len(prov["nodes"])
            self._log_line(f"Subscription loaded: {prov['host']} ({count} nodes)", "SUB")
            self._show_toast(f"Loaded {count} nodes from {prov['host']}", "success")

    def _on_subscription_error(self, pi, err):
        self._loading_subscriptions.pop(pi, None)
        if 0 <= pi < len(self.providers):
            prov = self.providers[pi]
            nodes = prov.get("nodes") or []
            if not nodes or all(n.get("_loading") for n in nodes):
                prov["nodes"] = []
            prov.pop("_subscription_url", None)
            self._rebuild_providers_ui()
            self._refresh_servers_page()
            self._log_line(f"Subscription fetch failed: {err}", "SUB")
            self._show_toast(f"Failed to load {prov['host']}: {err}", "error")

    def _refresh_subscription(self, pi):
        if 0 > pi or pi >= len(self.providers) or pi in self._loading_subscriptions:
            return
        prov = self.providers[pi]
        url = prov.get("url", "")
        if prov.get("type") != "SUB" or not url:
            return
        fetcher = SubFetchThread(url)
        fetcher.nodes_ready.connect(
            lambda nodes, p=pi: self._on_refresh_nodes(p, nodes)
        )
        fetcher.error.connect(
            lambda err, p=pi: self._on_refresh_error(p, err)
        )
        self._loading_subscriptions[pi] = fetcher
        self._log_line(f"Refreshing subscription: {prov['host']}", "SUB")
        self._show_toast(f"Refreshing {prov['host']}\u2026", "warning")
        fetcher.start()

    def _refresh_all_subscriptions(self):
        for pi, prov in enumerate(self.providers):
            if prov.get("type") == "SUB" and prov.get("url"):
                self._refresh_subscription(pi)

    def _on_refresh_nodes(self, pi, nodes):
        self._loading_subscriptions.pop(pi, None)
        if 0 <= pi < len(self.providers):
            prov = self.providers[pi]
            fav_hosts = {
                n.get("host") for n in prov.get("nodes", []) if n.get("_favorite")
            }
            if nodes:
                prov["nodes"] = nodes
                prov["parsed"] = nodes[0]
            else:
                prov["nodes"] = []
            for n in prov["nodes"]:
                if n.get("host") in fav_hosts:
                    n["_favorite"] = True
            if pi == self.selected_provider_index:
                self._configure_from_selection()
            self._rebuild_providers_ui()
            self._refresh_servers_page()
            self._save_state()
            self._log_line(
                f"Subscription refreshed: {prov['host']} ({len(prov['nodes'])} nodes)", "SUB"
            )
            self._show_toast(f"Refreshed {prov['host']}: {len(prov['nodes'])} nodes", "success")

    def _on_refresh_error(self, pi, err):
        self._loading_subscriptions.pop(pi, None)
        if 0 <= pi < len(self.providers):
            prov = self.providers[pi]
            self._log_line(f"Subscription refresh failed for {prov['host']}: {err}", "SUB")
            self._show_toast(f"Refresh failed for {prov['host']}: {err}", "error")

    def _pick_node(self, pi, ni):
        if pi < 0 or pi >= len(self.providers):
            return
        prov = self.providers[pi]
        nodes = prov.get("nodes", [])
        if not nodes or ni < 0 or ni >= len(nodes):
            return
        self.selected_provider_index = pi
        self.selected_node_index = ni
        self._configure_from_selection()
        self._refresh_server_pick()
        self._save_state()
        node = nodes[ni]
        self._show_toast(
            f"Node selected: {node.get('host', '?')}:{node.get('port', '?')}", "success"
        )

    def _toggle_favorite(self, pi, ni):
        if pi < 0 or pi >= len(self.providers):
            return
        prov = self.providers[pi]
        nodes = prov.get("nodes", [])
        if not nodes or ni < 0 or ni >= len(nodes):
            return
        node = nodes[ni]
        fav = not node.get("_favorite")
        node["_favorite"] = fav
        self._refresh_server_pick()
        self._refresh_servers_page()
        self._save_state()
        name = node.get("host", "?")
        if fav:
            self._log_line(f"Added to favorites: {name}", "FAV")
            self._show_toast(f"Added to favorites: {name}", "success")
        else:
            self._log_line(f"Removed from favorites: {name}", "FAV")
            self._show_toast(f"Removed from favorites: {name}")

    def _build_connect_section(self):
        wrap = QWidget()
        wrap.setFixedHeight(76)
        lo = QVBoxLayout()
        lo.setContentsMargins(0, 4, 0, 0)
        lo.setSpacing(0)
        wrap.setLayout(lo)

        self.connect_btn = ConnectButton()
        self.connect_btn.clicked.connect(self.toggle_connection)
        lo.addWidget(self.connect_btn, alignment=Qt.AlignCenter)
        return wrap

    # ---------- traffic ----------

    def _build_traffic_section(self):
        self.traffic_stack = QStackedWidget()
        self.traffic_stack.setFixedHeight(150)
        self.traffic_stack.addWidget(self._build_traffic_idle_page())
        self.traffic_stack.addWidget(self._build_traffic_active_page())
        self.traffic_stack.setCurrentIndex(0)
        self._traffic_active = False
        return self.traffic_stack

    def _build_traffic_idle_page(self):
        card = QWidget()
        card.setObjectName("card_traffic_idle")
        card.setStyleSheet(
            f"QWidget#card_traffic_idle {{ background: transparent; "
            f"border: 1px dashed {BORDER_HOVER}; border-radius: 16px; }}"
        )
        lo = QVBoxLayout()
        lo.setContentsMargins(20, 16, 20, 16)
        lo.setSpacing(8)
        card.setLayout(lo)

        icon = QLabel("\u21C4")
        icon.setFixedSize(38, 38)
        icon.setAlignment(Qt.AlignCenter)
        icon.setStyleSheet(
            f"background: {hex_rgba(ACCENT, 0.12)}; color: {ACCENT_LIGHT}; "
            "border-radius: 19px; font-size: 15px; font-weight: bold;"
        )
        lo.addWidget(icon, alignment=Qt.AlignCenter)

        title = QLabel("Live Traffic")
        title.setStyleSheet(f"color: {TEXT_PRI}; font-size: 13px; font-weight: 700;")
        title.setAlignment(Qt.AlignCenter)
        lo.addWidget(title)

        desc = QLabel("Connect to a node to see real-time download and upload rates")
        desc.setStyleSheet(f"color: {TEXT_DIM}; font-size: 10.5px;")
        desc.setAlignment(Qt.AlignCenter)
        lo.addWidget(desc)

        self.session_pill_idle = self._session_pill()
        lo.addWidget(self.session_pill_idle, alignment=Qt.AlignCenter)
        return card

    def _build_traffic_active_page(self):
        page = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        page.setLayout(layout)

        header = QLabel("TRAFFIC")
        header.setStyleSheet(
            f"color: {TEXT_PRI}; font-size: 13px; font-weight: 800; letter-spacing: 1.5px;"
        )
        layout.addWidget(header)

        blocks = QHBoxLayout()
        blocks.setSpacing(12)
        self.dl_graph = TrafficGraph(mode="download")
        self.ul_graph = TrafficGraph(mode="upload")
        self.ping_graph = TrafficGraph(mode="ping")
        dl_block = self._traffic_block("DOWNLOAD", CYAN, self.dl_graph, "down")
        ul_block = self._traffic_block("UPLOAD", RED, self.ul_graph, "up")
        ping_block = self._traffic_block("LATENCY", GREEN, self.ping_graph, "ping")
        blocks.addWidget(dl_block, 1)
        blocks.addWidget(ul_block, 1)
        blocks.addWidget(ping_block, 1)
        layout.addLayout(blocks, 1)

        self.session_pill_active = self._session_pill()
        layout.addWidget(self.session_pill_active, alignment=Qt.AlignCenter)
        return page

    def _traffic_block(self, label, color, graph, speed_attr):
        block = QWidget()
        block.setObjectName("card_traffic")
        block.setStyleSheet(card_qss("#card_traffic", radius=14, hover=False))
        self._elevate(block, blur=22, y=5)
        layout = QVBoxLayout()
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(4)
        block.setLayout(layout)

        lbl = QLabel(label)
        lbl.setStyleSheet(
            f"color: {color}; font-size: 10px; font-weight: 700; letter-spacing: 1.5px;"
        )
        layout.addWidget(lbl)
        layout.addWidget(graph, 1)

        speed_label = QLabel("0 B/s")
        speed_label.setStyleSheet(f"color: {TEXT_SEC}; font-size: 11px;")
        layout.addWidget(speed_label)
        if speed_attr == "down":
            self.graph_down_label = speed_label
        elif speed_attr == "up":
            self.graph_up_label = speed_label
        else:
            self.graph_ping_label = speed_label
        return block

    def _session_pill(self):
        btn = QPushButton("Session Total: 0 B")
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet(ghost_btn_qss(padding="4px 14px", radius=14, font_size=10.5))
        btn.setToolTip("Click to reset session counter")
        btn.clicked.connect(self._reset_session)
        return btn

    def _set_session_text(self):
        total = self.session_down + self.session_up
        text = f"Session Total: {self._format_size(total)}"
        self.session_pill_idle.setText(text)
        self.session_pill_active.setText(text)

    def _set_traffic_active(self, active):
        if self._traffic_active == active:
            return
        self._traffic_active = active
        self.traffic_stack.setCurrentIndex(1 if active else 0)
        self._fade_in_widget(self.traffic_stack)

    # ---------- servers page ----------

    def _build_servers_page(self):
        page = QWidget()
        page.setObjectName("pageServers")
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(10)
        page.setLayout(layout)

        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)
        header_row.setSpacing(8)

        header_col = QVBoxLayout()
        header_col.setSpacing(1)
        header = QLabel("Servers")
        header.setStyleSheet(f"color: {TEXT_PRI}; font-size: 18px; font-weight: 800;")
        header_col.addWidget(header)
        sub = QLabel("providers and their nodes")
        sub.setStyleSheet(f"color: {TEXT_DIM}; font-size: 10px;")
        header_col.addWidget(sub)
        header_row.addLayout(header_col)
        header_row.addStretch()

        self.btn_add_provider = QPushButton("+  Add Provider")
        self.btn_add_provider.setCursor(Qt.PointingHandCursor)
        self.btn_add_provider.setStyleSheet(ghost_btn_qss(padding="6px 14px"))
        self.btn_add_provider.clicked.connect(self.show_add_config_dialog)
        header_row.addWidget(self.btn_add_provider)

        layout.addLayout(header_row)

        self.servers_scroll = QScrollArea()
        self.servers_scroll.setWidgetResizable(True)
        self.servers_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.servers_container = QWidget()
        self.servers_container.setObjectName("serversContainer")
        self.servers_container.setMinimumWidth(600)
        self.servers_grid = QVBoxLayout()
        self.servers_grid.setContentsMargins(0, 0, 0, 0)
        self.servers_grid.setSpacing(8)
        self.servers_container.setLayout(self.servers_grid)
        self.servers_scroll.setWidget(self.servers_container)
        layout.addWidget(self.servers_scroll, 1)

        self.servers_empty = QWidget()
        empty_lo = QVBoxLayout()
        empty_lo.setSpacing(8)
        self.servers_empty.setLayout(empty_lo)
        empty_icon = QLabel("\u25C8")
        empty_icon.setStyleSheet(f"color: {TEXT_DIM}; font-size: 26px;")
        empty_icon.setAlignment(Qt.AlignCenter)
        empty_lo.addWidget(empty_icon)
        empty_title = QLabel("No providers yet")
        empty_title.setStyleSheet(f"color: {TEXT_SEC}; font-size: 13px; font-weight: bold;")
        empty_title.setAlignment(Qt.AlignCenter)
        empty_lo.addWidget(empty_title)
        empty_hint = QLabel(
            "Click \u201c+ Add Provider\u201d to add a subscription or a single link"
        )
        empty_hint.setStyleSheet(f"color: {TEXT_DIM}; font-size: 11px;")
        empty_hint.setAlignment(Qt.AlignCenter)
        empty_lo.addWidget(empty_hint)
        layout.addWidget(self.servers_empty)
        return page

    def _refresh_servers_page(self):
        for i in reversed(range(self.servers_grid.count())):
            w = self.servers_grid.itemAt(i).widget()
            if w:
                w.deleteLater()
        self._provider_folders = {}
        self._lat_labels = {}
        if not self.providers:
            self.servers_empty.show()
            self.servers_scroll.hide()
            return
        self.servers_empty.hide()
        self.servers_scroll.show()
        for pi, prov in enumerate(self.providers):
            self.servers_grid.addWidget(self._build_provider_section(pi, prov))
        self.servers_grid.addStretch()

    def _build_provider_section(self, pi, prov):
        section = QWidget()
        v = QVBoxLayout()
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(4)
        section.setLayout(v)

        header = QWidget()
        header.setObjectName("prov_header")
        header.setCursor(Qt.PointingHandCursor)
        header.setStyleSheet(
            f"QWidget#prov_header {{ background: {CARD}; border: 1px solid {BORDER}; "
            f"border-radius: 10px; }}"
            f"QWidget#prov_header:hover {{ background: {CARD_HOVER}; "
            f"border: 1px solid {BORDER_HOVER}; }}"
        )
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(14, 4, 8, 4)
        header_layout.setSpacing(6)
        header.setLayout(header_layout)

        header_btn = QPushButton()
        header_btn.setObjectName("prov_header_btn")
        header_btn.setCursor(Qt.PointingHandCursor)
        header_btn.setStyleSheet(
            f"QPushButton#prov_header_btn {{ background: transparent; border: none; "
            f"text-align: left; color: {TEXT_PRI}; font-size: 12px; font-weight: bold; }}"
        )
        header_layout.addWidget(header_btn, 1)

        refresh_btn = QPushButton("\u27F3")
        refresh_btn.setFixedSize(28, 28)
        refresh_btn.setCursor(Qt.PointingHandCursor)
        refresh_btn.setToolTip("Refresh subscription")
        refresh_btn.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {TEXT_SEC}; border: none; "
            f"border-radius: 14px; font-size: 13px; }}"
            f"QPushButton:hover {{ background: {hex_rgba(ACCENT, 0.15)}; color: {ACCENT_LIGHT}; }}"
        )
        refresh_btn.clicked.connect(lambda checked, i=pi: self._refresh_subscription(i))
        header_layout.addWidget(refresh_btn)
        if prov.get("type") != "SUB":
            refresh_btn.hide()

        body = QWidget()
        body_layout = QGridLayout()
        body_layout.setContentsMargins(14, 0, 4, 0)
        body_layout.setHorizontalSpacing(8)
        body_layout.setVerticalSpacing(6)
        body.setLayout(body_layout)

        folder = self._provider_folders.get(pi)
        expanded = folder["expanded"] if folder else True

        nodes = prov.get("nodes", [])
        for ni, node in enumerate(nodes):
            body_layout.addWidget(self._build_node_card(pi, ni, node), ni // 2, ni % 2)
        body_layout.setColumnStretch(0, 1)
        body_layout.setColumnStretch(1, 1)
        body_layout.setColumnMinimumWidth(0, 300)
        body_layout.setColumnMinimumWidth(1, 300)

        if not expanded:
            body.setMaximumHeight(0)
            body.hide()

        self._provider_folders[pi] = {"header": header_btn, "body": body, "expanded": expanded}
        self._update_folder_header(pi)

        header_btn.clicked.connect(lambda checked, i=pi: self._toggle_provider_folder(i))

        v.addWidget(header)
        v.addWidget(body)
        return section

    def _update_folder_header(self, pi):
        folder = self._provider_folders.get(pi)
        if not folder:
            return
        prov = self.providers[pi]
        nodes = prov.get("nodes", [])
        n_nodes = len(nodes)
        loading = any(n.get("_loading") for n in nodes)
        n_ok = sum(1 for n in nodes if n.get("host") and not n.get("_loading"))
        n_fav = sum(1 for n in nodes if n.get("_favorite"))
        arrow = "\u25BE" if folder["expanded"] else "\u25B8"
        fav_part = f"  \u00b7  \u2605 {n_fav}" if n_fav else ""
        load_part = "  \u00b7  \u23F3 loading\u2026" if loading else ""
        folder["header"].setText(
            f"{arrow}  {prov['host']}  \u00b7  [{prov.get('type', '?')}]  \u00b7  "
            f"{n_nodes} node{'s' if n_nodes != 1 else ''} ({n_ok} reachable){fav_part}{load_part}"
        )

    def _toggle_provider_folder(self, pi):
        folder = self._provider_folders.get(pi)
        if not folder:
            return
        folder["expanded"] = not folder["expanded"]
        body = folder["body"]
        self._update_folder_header(pi)
        if folder["expanded"]:
            body.setMaximumHeight(0)
            body.show()
            self._animate_body(body, 0, body.sizeHint().height())
        else:
            self._animate_body(body, body.height(), 0)

    def _animate_body(self, body, start_h, end_h):
        anim = QPropertyAnimation(body, b"maximumHeight", self)
        anim.setDuration(200)
        anim.setStartValue(start_h)
        anim.setEndValue(end_h)
        anim.setEasingCurve(QEasingCurve.OutCubic)
        if end_h == 0:
            anim.finished.connect(body.hide)
        anim.start(QPropertyAnimation.DeleteWhenStopped)

    def _build_node_card(self, pi, ni, node):
        is_selected = (
            pi == self.selected_provider_index
            and ni == self.selected_node_index
        )
        lat = node.get("_latency")
        flag = node.get("_flag")
        country = node.get("_country")
        if flag is None:
            flag, country = detect_country(node)
            if flag is None:
                flag, country = "\U0001F310", "Неизвестно"
            node["_flag"], node["_country"] = flag, country

        display_name = node.get("ps") or node.get("name") or country or node.get("host", "?")

        card = QFrame()
        card.setObjectName("card_node")
        if is_selected:
            card.setStyleSheet(
                f"QFrame#card_node {{ background: {CARD_ACTIVE}; "
                f"border: 1.5px solid {ACCENT}; border-radius: 14px; }}"
            )
        else:
            card.setStyleSheet(
                f"QFrame#card_node {{ background: {CARD}; border: 1px solid {BORDER}; "
                f"border-radius: 14px; }}"
                f"QFrame#card_node:hover {{ background: {CARD_HOVER}; "
                f"border: 1px solid {BORDER_HOVER}; }}"
            )
        card.setFixedHeight(68)

        layout = QHBoxLayout()
        layout.setContentsMargins(14, 0, 12, 0)
        layout.setSpacing(12)
        card.setLayout(layout)

        # Flag
        flag_lbl = QLabel(flag)
        flag_lbl.setStyleSheet("font-size: 24px; background: transparent;")
        flag_lbl.setFixedWidth(34)
        layout.addWidget(flag_lbl)

        # Name + country subtitle
        text_col = QVBoxLayout()
        text_col.setSpacing(2)
        text_col.setContentsMargins(0, 0, 0, 0)

        name_lbl = QLabel(display_name)
        name_lbl.setStyleSheet(
            f"color: {TEXT_PRI}; font-size: 13px; font-weight: 700; background: transparent;"
        )
        text_col.addWidget(name_lbl)

        if node.get("_loading"):
            sub_lbl = QLabel("Загрузка…")
            sub_lbl.setStyleSheet(f"color: {CYAN}; font-size: 10px; background: transparent;")
            text_col.addWidget(sub_lbl)
            layout.addLayout(text_col, 1)
            return card

        sub_text = country if country and country != display_name else ""
        sub_lbl = QLabel(sub_text)
        sub_lbl.setStyleSheet(f"color: {TEXT_DIM}; font-size: 10px; background: transparent;")
        text_col.addWidget(sub_lbl)
        layout.addLayout(text_col, 1)

        # Latency
        if lat is not None:
            c = GREEN if lat >= 0 and lat < 100 else (YELLOW if lat >= 0 and lat < 250 else RED)
            lat_text = f"{lat} ms" if lat >= 0 else "—"
            lat_lbl = QLabel(lat_text)
            lat_lbl.setStyleSheet(
                f"color: {c}; font-size: 11px; font-weight: 700; background: transparent;"
            )
        else:
            lat_lbl = QLabel("")
            lat_lbl.setStyleSheet(f"color: {TEXT_DIM}; font-size: 11px; background: transparent;")
        self._lat_labels[(pi, ni)] = lat_lbl
        layout.addWidget(lat_lbl)

        # Favorite button
        fav_btn = QPushButton("★" if node.get("_favorite") else "☆")
        fav_btn.setFixedSize(28, 28)
        fav_btn.setCursor(Qt.PointingHandCursor)
        fav_btn.setToolTip("Убрать из избранных" if node.get("_favorite") else "Добавить в избранные")
        fav_btn.setStyleSheet(self._fav_btn_qss(node.get("_favorite")))
        fav_btn.clicked.connect(lambda checked, pi=pi, ni=ni: self._toggle_favorite(pi, ni))
        layout.addWidget(fav_btn)

        # Connect button
        connect_btn = QPushButton("⚡ Connect")
        connect_btn.setFixedSize(80, 28)
        connect_btn.setCursor(Qt.PointingHandCursor)
        connect_btn.setStyleSheet(
            f"QPushButton {{ background: {GRAD_CONNECT}; color: white; border: none; "
            f"border-radius: 8px; font-size: 10px; font-weight: bold; }}"
            f"QPushButton:hover {{ opacity: 0.85; }}"
        )
        connect_btn.clicked.connect(lambda checked, pi=pi, ni=ni: self._select_and_connect(pi, ni))
        layout.addWidget(connect_btn)

        # Select button
        if is_selected:
            sel_btn = QPushButton("✓")
            sel_btn.setFixedSize(28, 28)
            sel_btn.setStyleSheet(
                f"QPushButton {{ background: {CARD_ACTIVE}; color: {ACCENT_LIGHT}; "
                f"border: 1.5px solid {ACCENT}; border-radius: 8px; font-size: 13px; font-weight: bold; }}"
            )
        else:
            sel_btn = QPushButton("○")
            sel_btn.setFixedSize(28, 28)
            sel_btn.setStyleSheet(ghost_btn_qss(radius=8, padding="0px", font_size=12))
        sel_btn.setCursor(Qt.PointingHandCursor)
        sel_btn.setToolTip("Выбрать без подключения")
        sel_btn.clicked.connect(lambda checked, pi=pi, ni=ni: self._select_node(pi, ni))
        layout.addWidget(sel_btn)

        return card

    # ---------- settings page ----------

    def _build_settings_page(self):
        scroll = QScrollArea()
        scroll.setObjectName("pageSettings")
        scroll.setWidgetResizable(True)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        content = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(26, 22, 26, 22)
        layout.setSpacing(8)
        content.setLayout(layout)

        title = QLabel("Settings")
        title.setStyleSheet(f"color: {TEXT_PRI}; font-size: 18px; font-weight: 800;")
        layout.addWidget(title)
        layout.addSpacing(4)

        def _section(text):
            lbl = QLabel(text)
            lbl.setStyleSheet(
                f"color: {TEXT_DIM}; font-size: 9.5px; font-weight: 700; "
                "letter-spacing: 2px; padding: 6px 4px 2px 4px;"
            )
            return lbl

        layout.addWidget(_section("APPEARANCE"))
        layout.addWidget(self._build_theme_card())

        layout.addWidget(_section("CONNECTION"))
        self.cb_system_proxy = SwitchToggle()
        self.cb_system_proxy.toggled.connect(self._save_state)
        layout.addWidget(self._setting_card(
            "System Proxy", "Route system traffic via 127.0.0.1:10809",
            self.cb_system_proxy,
        ))
        self.cb_tun_mode = SwitchToggle()
        self.cb_tun_mode.toggled.connect(self._save_state)
        layout.addWidget(self._setting_card(
            "TUN Mode", "Transparent tunneling of all traffic",
            self.cb_tun_mode,
        ))
        self.cb_autoconnect = SwitchToggle()
        self.cb_autoconnect.toggled.connect(self._save_state)
        layout.addWidget(self._setting_card(
            "Auto-Connect on Launch", "Connect automatically when app starts",
            self.cb_autoconnect,
        ))
        self.cb_smart_connect = SwitchToggle()
        self.cb_smart_connect.toggled.connect(self._save_state)
        layout.addWidget(self._setting_card(
            "Smart Connect", "Auto-pick the fastest node on launch or when the tunnel drops",
            self.cb_smart_connect,
        ))

        layout.addWidget(_section("ROUTING"))
        layout.addWidget(self._build_routing_card())

        layout.addWidget(_section("PRIVACY & SAFETY"))
        self.cb_killswitch = SwitchToggle()
        self.cb_killswitch.toggled.connect(self._save_state)
        layout.addWidget(self._setting_card(
            "DNS Leak Protection", "Block traffic if the tunnel drops",
            self.cb_killswitch,
        ))

        layout.addWidget(_section("NOTIFICATIONS"))
        self.cb_notifications = SwitchToggle()
        self.cb_notifications.toggled.connect(self._save_state)
        layout.addWidget(self._setting_card(
            "Notifications", "Show toast notifications",
            self.cb_notifications,
        ))

        layout.addWidget(_section("SPLIT TUNNELING"))
        layout.addWidget(self._build_split_tunnel_card())

        layout.addWidget(_section("DNS OVERRIDE"))
        layout.addWidget(self._build_dns_card())

        layout.addWidget(_section("IPV6 SUPPORT"))
        layout.addWidget(self._build_ipv6_card())

        layout.addWidget(_section("XRAY UPDATER"))
        layout.addWidget(self._build_xray_updater_card())

        layout.addWidget(_section("APP KILL SWITCH"))
        layout.addWidget(self._build_app_killswitch_card())

        layout.addWidget(_section("BACKUP"))
        layout.addWidget(self._build_backup_card())

        layout.addStretch()

        about = QLabel("ZIFY VPN v4.2 PREMIUM \u00b7 PYSIDE6 \u00b7 XRAY-CORE")
        about.setStyleSheet(
            f"color: {TEXT_DIM}; font-size: 9px; font-weight: 600; letter-spacing: 1.2px;"
        )
        about.setAlignment(Qt.AlignCenter)
        layout.addWidget(about)

        scroll.setWidget(content)
        return scroll

    def _build_theme_card(self):
        card = QWidget()
        card.setObjectName("card_theme")
        card.setStyleSheet(card_qss("#card_theme", radius=14, hover=False))
        self._elevate(card, blur=22, y=5)
        lo = QHBoxLayout()
        lo.setContentsMargins(18, 14, 18, 14)
        lo.setSpacing(12)
        card.setLayout(lo)

        left = QVBoxLayout()
        left.setSpacing(2)
        lbl = QLabel("Theme")
        lbl.setStyleSheet(f"color: {TEXT_PRI}; font-size: 13px; font-weight: 700;")
        left.addWidget(lbl)
        d = QLabel("Appearance color scheme")
        d.setStyleSheet(f"color: {TEXT_SEC}; font-size: 10.5px;")
        left.addWidget(d)
        lo.addLayout(left, 1)

        self.theme_combo = QComboBox()
        self.theme_combo.setFixedWidth(190)
        self.theme_combo.blockSignals(True)
        for name in theme.names():
            self.theme_combo.addItem(theme.DISPLAY.get(name, name), name)
        idx = self.theme_combo.findData(theme.current_name)
        self.theme_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self.theme_combo.blockSignals(False)
        self.theme_combo.currentIndexChanged.connect(self._on_theme_changed)
        lo.addWidget(self.theme_combo)
        return card

    def _setting_card(self, label_text, desc, control):
        card = QWidget()
        card.setObjectName("card_setting")
        card.setStyleSheet(card_qss("#card_setting", radius=14, hover=False))
        self._elevate(card, blur=22, y=5)
        lo = QHBoxLayout()
        lo.setContentsMargins(18, 14, 18, 14)
        lo.setSpacing(12)
        card.setLayout(lo)

        left = QVBoxLayout()
        left.setSpacing(2)
        lbl = QLabel(label_text)
        lbl.setStyleSheet(f"color: {TEXT_PRI}; font-size: 13px; font-weight: 700;")
        left.addWidget(lbl)
        if desc:
            d = QLabel(desc)
            d.setStyleSheet(f"color: {TEXT_SEC}; font-size: 10.5px;")
            left.addWidget(d)
        lo.addLayout(left, 1)
        lo.addWidget(control, 0, Qt.AlignVCenter | Qt.AlignRight)
        return card

    def _create_switch_card(self, label_text, desc, control):
        """Create a compact card for switch toggles in a row."""
        card = QWidget()
        card.setObjectName("card_setting")
        card.setStyleSheet(card_qss("#card_setting", radius=14, hover=False))
        self._elevate(card, blur=22, y=5)
        lo = QVBoxLayout()
        lo.setContentsMargins(10, 10, 10, 10)
        lo.setSpacing(4)
        card.setLayout(lo)

        if label_text:
            lbl = QLabel(label_text)
            lbl.setStyleSheet(f"color: {TEXT_PRI}; font-size: 11px; font-weight: 700;")
            lo.addWidget(lbl)
        if desc:
            d = QLabel(desc)
            d.setStyleSheet(f"color: {TEXT_SEC}; font-size: 9px;")
            lo.addWidget(d)
        
        # Wrap switch in container with fixed width
        control_container = QWidget()
        control_container.setFixedWidth(60)
        control_layout = QHBoxLayout()
        control_layout.setContentsMargins(0, 0, 0, 0)
        control_layout.setSpacing(0)
        control_layout.addWidget(control)
        control_container.setLayout(control_layout)
        lo.addWidget(control_container)
        return card

    # ---------- routing ----------

    def _build_routing_card(self):
        card = QWidget()
        card.setObjectName("card_routing")
        card.setStyleSheet(card_qss("#card_routing", radius=14, hover=False))
        self._elevate(card, blur=22, y=5)
        lo = QVBoxLayout()
        lo.setContentsMargins(18, 14, 18, 14)
        lo.setSpacing(10)
        card.setLayout(lo)

        row = QHBoxLayout()
        row.setSpacing(12)
        left = QVBoxLayout()
        left.setSpacing(2)
        lbl = QLabel("Routing Mode")
        lbl.setStyleSheet(f"color: {TEXT_PRI}; font-size: 13px; font-weight: 700;")
        d = QLabel("Choose how traffic is routed through the tunnel")
        d.setStyleSheet(f"color: {TEXT_SEC}; font-size: 10.5px;")
        left.addWidget(lbl)
        left.addWidget(d)
        row.addLayout(left, 1)
        self.routing_combo = QComboBox()
        self.routing_combo.setFixedWidth(250)
        self.routing_combo.addItem("All traffic through VPN", "all")
        self.routing_combo.addItem("Bypass blocked sites (RU direct)", "bypass")
        self.routing_combo.addItem("Direct local network only", "lan")
        self.routing_combo.currentIndexChanged.connect(self._save_state)
        row.addWidget(self.routing_combo)
        lo.addLayout(row)

        dom_row = QHBoxLayout()
        dom_row.setSpacing(8)
        self.routing_input = QLineEdit()
        self.routing_input.setPlaceholderText("Add bypass domain, e.g. example.com")
        self.routing_input.setStyleSheet(
            f"QLineEdit {{ background: {theme.current['MENU_BG']}; color: {TEXT_PRI}; "
            f"border: 1px solid {BORDER}; border-radius: 9px; padding: 7px 12px; "
            f"font-size: 11px; }}"
            f"QLineEdit:focus {{ border: 1px solid {ACCENT}; }}"
        )
        self.routing_input.returnPressed.connect(self._add_routing_domain)
        dom_row.addWidget(self.routing_input, 1)
        btn_add = QPushButton("Add")
        btn_add.setCursor(Qt.PointingHandCursor)
        btn_add.setStyleSheet(ghost_btn_qss(padding="6px 16px", radius=8))
        btn_add.clicked.connect(self._add_routing_domain)
        dom_row.addWidget(btn_add)
        lo.addLayout(dom_row)

        self.routing_domains_list = QVBoxLayout()
        self.routing_domains_list.setContentsMargins(0, 0, 0, 0)
        self.routing_domains_list.setSpacing(4)
        self.routing_domains_wrap = QWidget()
        self.routing_domains_wrap.setLayout(self.routing_domains_list)
        lo.addWidget(self.routing_domains_wrap)
        return card

    def _rebuild_routing_domains(self):
        if not hasattr(self, "routing_domains_list"):
            return
        for i in reversed(range(self.routing_domains_list.count())):
            w = self.routing_domains_list.itemAt(i).widget()
            if w:
                w.deleteLater()
        for idx, dom in enumerate(self._routing_domains):
            row = QWidget()
            h = QHBoxLayout()
            h.setContentsMargins(0, 0, 0, 0)
            h.setSpacing(6)
            row.setLayout(h)
            lbl = QLabel(dom)
            lbl.setStyleSheet(
                f"background: {hex_rgba(ACCENT, 0.12)}; color: {ACCENT_LIGHT}; "
                f"font-size: 10px; font-weight: 600; border-radius: 6px; padding: 4px 10px;"
            )
            rm = QPushButton("\u2715")
            rm.setFixedSize(20, 20)
            rm.setCursor(Qt.PointingHandCursor)
            rm.setStyleSheet(
                f"QPushButton {{ background: transparent; color: {TEXT_DIM}; border: none; "
                f"font-size: 9px; border-radius: 10px; }}"
                f"QPushButton:hover {{ background: {hex_rgba(RED, 0.2)}; color: {RED}; }}"
            )
            rm.clicked.connect(lambda checked, i=idx: self._remove_routing_domain(i))
            h.addWidget(lbl)
            h.addWidget(rm)
            h.addStretch()
            self.routing_domains_list.addWidget(row)

    def _add_routing_domain(self):
        text = self.routing_input.text().strip().lower()
        if not text or text in self._routing_domains:
            return
        self._routing_domains.append(text)
        self.routing_input.clear()
        self._rebuild_routing_domains()
        self._save_state()
        self._log_line(f"Bypass domain added: {text}", "ROUTE")
        self._show_toast(f"Bypass domain added: {text}", "success")

    def _remove_routing_domain(self, idx):
        if 0 <= idx < len(self._routing_domains):
            self._routing_domains.pop(idx)
        self._rebuild_routing_domains()
        self._save_state()

    def _add_split_app(self):
        if not hasattr(self, 'split_app_input') or self.split_app_input is None:
            return
        text = self.split_app_input.text().strip()
        if not text or text in self._split_apps:
            return
        self._split_apps.append(text)
        self.split_app_input.clear()
        self._rebuild_split_apps()
        self._save_state()
        self._log_line(f"Split tunnel app added: {text}", "SPLIT")
        self._show_toast(f"Added to split tunnel: {text}", "success")

    def _remove_split_app(self, idx):
        if 0 <= idx < len(self._split_apps):
            self._split_apps.pop(idx)
        self._rebuild_split_apps()
        self._save_state()

    def _rebuild_split_apps(self):
        if not hasattr(self, "split_apps_list"):
            return
        for i in reversed(range(self.split_apps_list.count())):
            w = self.split_apps_list.itemAt(i).widget()
            if w:
                w.deleteLater()
        for idx, app in enumerate(self._split_apps):
            row = QWidget()
            h = QHBoxLayout()
            h.setContentsMargins(0, 0, 0, 0)
            h.setSpacing(6)
            row.setLayout(h)
            lbl = QLabel(os.path.basename(app))
            lbl.setStyleSheet(
                f"background: {hex_rgba(ACCENT, 0.12)}; color: {ACCENT_LIGHT}; "
                f"font-size: 10px; font-weight: 600; border-radius: 6px; padding: 4px 10px;"
            )
            rm = QPushButton("\u2715")
            rm.setFixedSize(20, 20)
            rm.setCursor(Qt.PointingHandCursor)
            rm.setStyleSheet(
                f"QPushButton {{ background: transparent; color: {TEXT_DIM}; border: none; "
                f"font-size: 9px; border-radius: 10px; }}"
                f"QPushButton:hover {{ background: {hex_rgba(RED, 0.2)}; color: {RED}; }}"
            )
            rm.clicked.connect(lambda checked, i=idx: self._remove_split_app(i))
            h.addWidget(lbl)
            h.addWidget(rm)
            h.addStretch()
            self.split_apps_list.addWidget(row)

    def _browse_split_app(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Application", "", "Executable Files (*.exe);;All Files (*)"
        )
        if path:
            self.split_app_input.setText(path)
            self._add_split_app()

    def _refresh_split_apps(self):
        processes = get_running_processes()
        if processes:
            self._show_toast(f"Found {len(processes)} running processes", "success")
            # Show first 5 processes as example
            example = [p["name"] for p in processes[:5]]
            self._log_line(f"Running processes: {', '.join(example)}", "SPLIT")
        else:
            self._show_toast("No running processes found", "warning")

    def _on_dns_changed(self, index):
        dns_id = self.dns_combo.itemData(index)
        if dns_id == "custom":
            self.custom_dns_input.show()
        else:
            self.custom_dns_input.hide()
        self._save_state()

    def _check_for_updates(self):
        self.btn_check_update.setEnabled(False)
        self.update_status.setText("Checking...")
        self.update_status.setStyleSheet(f"color: {YELLOW}; font-size: 10.5px;")
        
        self.update_thread = UpdateCheckThread()
        self.update_thread.result.connect(self._on_update_check_done)
        self.update_thread.start()

    def _on_update_check_done(self, result):
        self.btn_check_update.setEnabled(True)
        if result and "error" not in result:
            if result.get("current") != result.get("latest"):
                self.update_status.setText(f"Update available: v{result['latest']}")
                self.update_status.setStyleSheet(f"color: {GREEN}; font-size: 10.5px;")
                self.btn_download_update.show()
            else:
                self.update_status.setText("Up to date")
                self.update_status.setStyleSheet(f"color: {GREEN}; font-size: 10.5px;")
        else:
            error_msg = result.get("error", "Unknown error") if result else "Unknown error"
            self.update_status.setText(f"Error: {error_msg}")
            self.update_status.setStyleSheet(f"color: {RED}; font-size: 10.5px;")

    def _download_update(self):
        self.btn_download_update.setEnabled(False)
        self.update_status.setText("Downloading...")
        self.update_status.setStyleSheet(f"color: {YELLOW}; font-size: 10.5px;")
        
        def worker():
            success, message = download_xray_update()
            self._on_update_download_done(success, message)
        
        self.download_thread = QThread()
        self.download_thread.run = worker
        self.download_thread.finished.connect(self.download_thread.deleteLater)
        self.download_thread.start()

    def _on_update_download_done(self, success, message):
        self.btn_download_update.setEnabled(True)
        if success:
            self.update_status.setText(message)
            self.update_status.setStyleSheet(f"color: {GREEN}; font-size: 10.5px;")
            self._show_toast(message, "success")
        else:
            self.update_status.setText(f"Error: {message}")
            self.update_status.setStyleSheet(f"color: {RED}; font-size: 10.5px;")
            self._show_toast(message, "error")

    def _add_killswitch_app(self):
        text = self.killswitch_app_input.text().strip()
        if not text or text in self._killswitch_apps:
            return
        self._killswitch_apps.append(text)
        self.killswitch_app_input.clear()
        self._rebuild_killswitch_apps()
        self._save_state()
        self._log_line(f"Killswitch app added: {text}", "KS")
        self._show_toast(f"Added to killswitch: {text}", "success")

    def _remove_killswitch_app(self, idx):
        if 0 <= idx < len(self._killswitch_apps):
            self._killswitch_apps.pop(idx)
        self._rebuild_killswitch_apps()
        self._save_state()

    def _rebuild_killswitch_apps(self):
        if not hasattr(self, "killswitch_apps_list"):
            return
        for i in reversed(range(self.killswitch_apps_list.count())):
            w = self.killswitch_apps_list.itemAt(i).widget()
            if w:
                w.deleteLater()
        for idx, app in enumerate(self._killswitch_apps):
            row = QWidget()
            h = QHBoxLayout()
            h.setContentsMargins(0, 0, 0, 0)
            h.setSpacing(6)
            row.setLayout(h)
            lbl = QLabel(os.path.basename(app))
            lbl.setStyleSheet(
                f"background: {hex_rgba(RED, 0.12)}; color: {RED}; "
                f"font-size: 10px; font-weight: 600; border-radius: 6px; padding: 4px 10px;"
            )
            rm = QPushButton("\u2715")
            rm.setFixedSize(20, 20)
            rm.setCursor(Qt.PointingHandCursor)
            rm.setStyleSheet(
                f"QPushButton {{ background: transparent; color: {TEXT_DIM}; border: none; "
                f"font-size: 9px; border-radius: 10px; }}"
                f"QPushButton:hover {{ background: {hex_rgba(RED, 0.2)}; color: {RED}; }}"
            )
            rm.clicked.connect(lambda checked, i=idx: self._remove_killswitch_app(i))
            h.addWidget(lbl)
            h.addWidget(rm)
            h.addStretch()
            self.killswitch_apps_list.addWidget(row)

    def _browse_killswitch_app(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Application", "", "Executable Files (*.exe);;All Files (*)"
        )
        if path:
            self.killswitch_app_input.setText(path)
            self._add_killswitch_app()

    def _refresh_killswitch_apps(self):
        processes = get_running_processes()
        if processes:
            self._show_toast(f"Found {len(processes)} running processes", "success")
            example = [p["name"] for p in processes[:5]]
            self._log_line(f"Running processes: {', '.join(example)}", "KS")
        else:
            self._show_toast("No running processes found", "warning")

    # ---------- backup ----------

    def _build_backup_card(self):
        card = QWidget()
        card.setObjectName("card_backup")
        card.setStyleSheet(card_qss("#card_backup", radius=14, hover=False))
        self._elevate(card, blur=22, y=5)
        lo = QHBoxLayout()
        lo.setContentsMargins(18, 14, 18, 14)
        lo.setSpacing(12)
        card.setLayout(lo)
        left = QVBoxLayout()
        left.setSpacing(2)
        lbl = QLabel("Backup & Restore")
        lbl.setStyleSheet(f"color: {TEXT_PRI}; font-size: 13px; font-weight: 700;")
        d = QLabel("Save providers and settings to a file, or restore them")
        d.setStyleSheet(f"color: {TEXT_SEC}; font-size: 10.5px;")
        left.addWidget(lbl)
        left.addWidget(d)
        lo.addLayout(left, 1)
        btn_exp = QPushButton("\u2B07  Export")
        btn_exp.setCursor(Qt.PointingHandCursor)
        btn_exp.setStyleSheet(ghost_btn_qss(color=GREEN, padding="8px 18px"))
        btn_exp.clicked.connect(self._export_backup)
        lo.addWidget(btn_exp)
        btn_imp = QPushButton("\u2B06  Import")
        btn_imp.setCursor(Qt.PointingHandCursor)
        btn_imp.setStyleSheet(ghost_btn_qss(color=ACCENT, padding="8px 18px"))
        btn_imp.clicked.connect(self._import_backup)
        lo.addWidget(btn_imp)
        return card

    def _build_split_tunnel_card(self):
        card = QWidget()
        card.setObjectName("card_split_tunnel")
        card.setStyleSheet(card_qss("#card_split_tunnel", radius=14, hover=False))
        self._elevate(card, blur=22, y=5)
        lo = QVBoxLayout()
        lo.setContentsMargins(18, 14, 18, 14)
        lo.setSpacing(10)
        card.setLayout(lo)

        # Mode selector
        mode_row = QHBoxLayout()
        mode_row.setSpacing(12)
        left = QVBoxLayout()
        left.setSpacing(2)
        lbl = QLabel("Split Tunneling Mode")
        lbl.setStyleSheet(f"color: {TEXT_PRI}; font-size: 13px; font-weight: 700;")
        d = QLabel("Choose which apps use VPN")
        d.setStyleSheet(f"color: {TEXT_SEC}; font-size: 10.5px;")
        left.addWidget(lbl)
        left.addWidget(d)
        mode_row.addLayout(left, 1)
        
        self.split_mode_combo = QComboBox()
        self.split_mode_combo.setFixedWidth(250)
        self.split_mode_combo.addItem("All apps except selected (exclude)", "exclude")
        self.split_mode_combo.addItem("Only selected apps (include)", "include")
        self.split_mode_combo.currentIndexChanged.connect(self._save_state)
        mode_row.addWidget(self.split_mode_combo)
        lo.addLayout(mode_row)

        # Add app row
        add_row = QHBoxLayout()
        add_row.setSpacing(8)
        self.split_app_input = QLineEdit()
        self.split_app_input.setPlaceholderText("Add app path, e.g. C:\\Program Files\\Chrome\\chrome.exe")
        self.split_app_input.setStyleSheet(
            f"QLineEdit {{ background: {theme.current['MENU_BG']}; color: {TEXT_PRI}; "
            f"border: 1px solid {BORDER}; border-radius: 9px; padding: 7px 12px; "
            f"font-size: 11px; }}"
            f"QLineEdit:focus {{ border: 1px solid {ACCENT}; }}"
        )
        self.split_app_input.returnPressed.connect(self._add_split_app)
        add_row.addWidget(self.split_app_input, 1)
        
        btn_browse = QPushButton("Browse...")
        btn_browse.setCursor(Qt.PointingHandCursor)
        btn_browse.setStyleSheet(ghost_btn_qss(padding="6px 12px", radius=8))
        btn_browse.clicked.connect(self._browse_split_app)
        add_row.addWidget(btn_browse)
        
        btn_add = QPushButton("Add")
        btn_add.setCursor(Qt.PointingHandCursor)
        btn_add.setStyleSheet(ghost_btn_qss(color=ACCENT, padding="6px 16px", radius=8))
        btn_add.clicked.connect(self._add_split_app)
        add_row.addWidget(btn_add)
        lo.addLayout(add_row)

        # Apps list
        self.split_apps_list = QVBoxLayout()
        self.split_apps_list.setContentsMargins(0, 0, 0, 0)
        self.split_apps_list.setSpacing(4)
        self.split_apps_wrap = QWidget()
        self.split_apps_wrap.setLayout(self.split_apps_list)
        lo.addWidget(self.split_apps_wrap)
        
        # Refresh processes button
        btn_refresh = QPushButton("\u27F3  Refresh running processes")
        btn_refresh.setCursor(Qt.PointingHandCursor)
        btn_refresh.setStyleSheet(ghost_btn_qss(padding="4px 12px", radius=6, font_size=9))
        btn_refresh.clicked.connect(self._refresh_split_apps)
        lo.addWidget(btn_refresh)
        
        return card

    def _build_dns_card(self):
        card = QWidget()
        card.setObjectName("card_dns")
        card.setStyleSheet(card_qss("#card_dns", radius=14, hover=False))
        self._elevate(card, blur=22, y=5)
        lo = QVBoxLayout()
        lo.setContentsMargins(18, 14, 18, 14)
        lo.setSpacing(10)
        card.setLayout(lo)

        # DNS selector
        dns_row = QHBoxLayout()
        dns_row.setSpacing(12)
        left = QVBoxLayout()
        left.setSpacing(2)
        lbl = QLabel("DNS Server")
        lbl.setStyleSheet(f"color: {TEXT_PRI}; font-size: 13px; font-weight: 700;")
        d = QLabel("Choose DNS server for domain resolution")
        d.setStyleSheet(f"color: {TEXT_SEC}; font-size: 10.5px;")
        left.addWidget(lbl)
        left.addWidget(d)
        dns_row.addLayout(left, 1)
        
        self.dns_combo = QComboBox()
        self.dns_combo.setFixedWidth(250)
        for item in get_preset_dns_list():
            self.dns_combo.addItem(item["name"], item["id"])
        self.dns_combo.currentIndexChanged.connect(self._save_state)
        dns_row.addWidget(self.dns_combo)
        lo.addLayout(dns_row)

        # Custom DNS input (hidden by default)
        self.custom_dns_input = QLineEdit()
        self.custom_dns_input.setPlaceholderText("Custom DNS servers (comma-separated, e.g. 8.8.8.8,1.1.1.1)")
        self.custom_dns_input.setStyleSheet(
            f"QLineEdit {{ background: {theme.current['MENU_BG']}; color: {TEXT_PRI}; "
            f"border: 1px solid {BORDER}; border-radius: 9px; padding: 7px 12px; "
            f"font-size: 11px; }}"
            f"QLineEdit:focus {{ border: 1px solid {ACCENT}; }}"
        )
        self.custom_dns_input.returnPressed.connect(self._save_state)
        lo.addWidget(self.custom_dns_input)
        
        # Show custom input when "custom" is selected
        self.dns_combo.currentIndexChanged.connect(self._on_dns_changed)
        
        # Blockers
        block_row = QHBoxLayout()
        block_row.setSpacing(12)
        block_left = QVBoxLayout()
        block_left.setSpacing(2)
        block_lbl = QLabel("Blockers")
        block_lbl.setStyleSheet(f"color: {TEXT_PRI}; font-size: 13px; font-weight: 700;")
        block_d = QLabel("Block ads, trackers, and malware")
        block_d.setStyleSheet(f"color: {TEXT_SEC}; font-size: 10.5px;")
        block_left.addWidget(block_lbl)
        block_left.addWidget(block_d)
        block_row.addLayout(block_left, 1)
        
        # Create blocker cards with proper layout
        blockers_container = QWidget()
        blockers_layout = QHBoxLayout()
        blockers_layout.setContentsMargins(0, 0, 0, 0)
        blockers_layout.setSpacing(8)
        blockers_container.setLayout(blockers_layout)
        
        self.cb_block_ads = SwitchToggle()
        self.cb_block_ads.toggled.connect(self._save_state)
        blockers_layout.addWidget(self._create_switch_card("Block Ads", "", self.cb_block_ads))
        
        self.cb_block_trackers = SwitchToggle()
        self.cb_block_trackers.toggled.connect(self._save_state)
        blockers_layout.addWidget(self._create_switch_card("Block Trackers", "", self.cb_block_trackers))
        
        self.cb_block_malware = SwitchToggle()
        self.cb_block_malware.toggled.connect(self._save_state)
        blockers_layout.addWidget(self._create_switch_card("Block Malware", "", self.cb_block_malware))
        
        block_row.addWidget(blockers_container)
        lo.addLayout(block_row)
        
        return card

    def _build_ipv6_card(self):
        card = QWidget()
        card.setObjectName("card_ipv6")
        card.setStyleSheet(card_qss("#card_ipv6", radius=14, hover=False))
        self._elevate(card, blur=22, y=5)
        lo = QVBoxLayout()
        lo.setContentsMargins(18, 14, 18, 14)
        lo.setSpacing(10)
        card.setLayout(lo)

        self.cb_ipv6_enabled = SwitchToggle()
        self.cb_ipv6_enabled.toggled.connect(self._save_state)
        lo.addWidget(self._setting_card(
            "Enable IPv6", "Allow IPv6 traffic through VPN",
            self.cb_ipv6_enabled,
        ))
        
        self.cb_ipv6_dns = SwitchToggle()
        self.cb_ipv6_dns.toggled.connect(self._save_state)
        lo.addWidget(self._setting_card(
            "IPv6 DNS", "Use IPv6 for DNS resolution",
            self.cb_ipv6_dns,
        ))
        
        self.cb_ipv6_routing = SwitchToggle()
        self.cb_ipv6_routing.toggled.connect(self._save_state)
        lo.addWidget(self._setting_card(
            "IPv6 Routing", "Route IPv6 traffic through VPN",
            self.cb_ipv6_routing,
        ))
        
        self.cb_ipv6_prefer = SwitchToggle()
        self.cb_ipv6_prefer.toggled.connect(self._save_state)
        lo.addWidget(self._setting_card(
            "Prefer IPv6", "Prefer IPv6 connections when available",
            self.cb_ipv6_prefer,
        ))
        
        return card

    def _build_xray_updater_card(self):
        card = QWidget()
        card.setObjectName("card_updater")
        card.setStyleSheet(card_qss("#card_updater", radius=14, hover=False))
        self._elevate(card, blur=22, y=5)
        lo = QVBoxLayout()
        lo.setContentsMargins(18, 14, 18, 14)
        lo.setSpacing(10)
        card.setLayout(lo)

        # Auto update toggle
        self.cb_auto_update = SwitchToggle()
        self.cb_auto_update.toggled.connect(self._save_state)
        lo.addWidget(self._setting_card(
            "Auto-Update Xray", "Automatically check and install updates",
            self.cb_auto_update,
        ))

        # Check button
        check_row = QHBoxLayout()
        check_row.setSpacing(8)
        self.btn_check_update = QPushButton("\u27F3  Check for updates")
        self.btn_check_update.setCursor(Qt.PointingHandCursor)
        self.btn_check_update.setStyleSheet(ghost_btn_qss(color=ACCENT, padding="8px 16px", radius=8))
        self.btn_check_update.clicked.connect(self._check_for_updates)
        check_row.addWidget(self.btn_check_update)
        
        self.update_status = QLabel("")
        self.update_status.setStyleSheet(f"color: {TEXT_SEC}; font-size: 10.5px;")
        check_row.addWidget(self.update_status)
        check_row.addStretch()
        lo.addLayout(check_row)

        # Download button (hidden by default)
        self.btn_download_update = QPushButton("\u2B07  Download and install update")
        self.btn_download_update.setCursor(Qt.PointingHandCursor)
        self.btn_download_update.setStyleSheet(ghost_btn_qss(color=GREEN, padding="8px 16px", radius=8))
        self.btn_download_update.clicked.connect(self._download_update)
        self.btn_download_update.hide()
        lo.addWidget(self.btn_download_update)
        
        return card

    def _build_app_killswitch_card(self):
        card = QWidget()
        card.setObjectName("card_killswitch_apps")
        card.setStyleSheet(card_qss("#card_killswitch_apps", radius=14, hover=False))
        self._elevate(card, blur=22, y=5)
        lo = QVBoxLayout()
        lo.setContentsMargins(18, 14, 18, 14)
        lo.setSpacing(10)
        card.setLayout(lo)

        # Apps list
        apps_row = QHBoxLayout()
        apps_row.setSpacing(12)
        left = QVBoxLayout()
        left.setSpacing(2)
        lbl = QLabel("App Kill Switch")
        lbl.setStyleSheet(f"color: {TEXT_PRI}; font-size: 13px; font-weight: 700;")
        d = QLabel("Block selected apps when VPN disconnects")
        d.setStyleSheet(f"color: {TEXT_SEC}; font-size: 10.5px;")
        left.addWidget(lbl)
        left.addWidget(d)
        apps_row.addLayout(left, 1)
        lo.addLayout(apps_row)

        # Add app row
        add_row = QHBoxLayout()
        add_row.setSpacing(8)
        self.killswitch_app_input = QLineEdit()
        self.killswitch_app_input.setPlaceholderText("Add app path, e.g. C:\\Program Files\\Chrome\\chrome.exe")
        self.killswitch_app_input.setStyleSheet(
            f"QLineEdit {{ background: {theme.current['MENU_BG']}; color: {TEXT_PRI}; "
            f"border: 1px solid {BORDER}; border-radius: 9px; padding: 7px 12px; "
            f"font-size: 11px; }}"
            f"QLineEdit:focus {{ border: 1px solid {ACCENT}; }}"
        )
        self.killswitch_app_input.returnPressed.connect(self._add_killswitch_app)
        add_row.addWidget(self.killswitch_app_input, 1)
        
        btn_browse = QPushButton("Browse...")
        btn_browse.setCursor(Qt.PointingHandCursor)
        btn_browse.setStyleSheet(ghost_btn_qss(padding="6px 12px", radius=8))
        btn_browse.clicked.connect(self._browse_killswitch_app)
        add_row.addWidget(btn_browse)
        
        btn_add = QPushButton("Add")
        btn_add.setCursor(Qt.PointingHandCursor)
        btn_add.setStyleSheet(ghost_btn_qss(color=ACCENT, padding="6px 16px", radius=8))
        btn_add.clicked.connect(self._add_killswitch_app)
        add_row.addWidget(btn_add)
        lo.addLayout(add_row)

        # Apps list
        self.killswitch_apps_list = QVBoxLayout()
        self.killswitch_apps_list.setContentsMargins(0, 0, 0, 0)
        self.killswitch_apps_list.setSpacing(4)
        self.killswitch_apps_wrap = QWidget()
        self.killswitch_apps_wrap.setLayout(self.killswitch_apps_list)
        lo.addWidget(self.killswitch_apps_wrap)
        
        # Refresh processes button
        btn_refresh = QPushButton("\u27F3  Refresh running processes")
        btn_refresh.setCursor(Qt.PointingHandCursor)
        btn_refresh.setStyleSheet(ghost_btn_qss(padding="4px 12px", radius=6, font_size=9))
        btn_refresh.clicked.connect(self._refresh_killswitch_apps)
        lo.addWidget(btn_refresh)
        
        return card

    def _export_backup(self):
        default = os.path.join(os.path.expanduser("~"), "zify-backup.json")
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Backup", default, "Zify Backup (*.json)"
        )
        if not path:
            return
        try:
            storage.export_backup(
                path, self.providers, self.selected_provider_index,
                self.selected_node_index, self._collect_settings(),
            )
            self._log_line(f"Backup exported to {path}", "BACKUP")
            self._show_toast("Backup exported", "success")
        except Exception as e:
            self._log_line(f"Backup export failed: {e}", "BACKUP")
            self._show_toast(f"Export failed: {e}", "error")

    def _import_backup(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Import Backup", os.path.expanduser("~"), "Zify Backup (*.json)"
        )
        if not path:
            return
        try:
            items, sel_p, sel_n, settings = storage.import_backup(path)
            self._load_providers_from_items(items)
            self._settings_values = settings
            if hasattr(self, "cb_system_proxy"):
                self._apply_settings_values()
            if self.providers:
                if 0 <= sel_p < len(self.providers):
                    self._select_provider(sel_p, sel_n)
                else:
                    self._select_provider(0, 0)
                self._rebuild_providers_ui()
                self._refresh_servers_page()
                self._set_status("Configured", YELLOW)
            self._save_state()
            self._log_line(f"Backup imported from {path}", "BACKUP")
            self._show_toast("Backup imported", "success")
        except Exception as e:
            self._log_line(f"Backup import failed: {e}", "BACKUP")
            self._show_toast(f"Import failed: {e}", "error")

    # ---------- logs page ----------

    def _build_logs_page(self):
        page = QWidget()
        page.setObjectName("pageLogs")
        layout = QVBoxLayout()
        layout.setContentsMargins(26, 22, 26, 22)
        layout.setSpacing(12)
        page.setLayout(layout)

        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)
        header_row.setSpacing(8)
        header_col = QVBoxLayout()
        header_col.setSpacing(1)
        header = QLabel("Logs")
        header.setStyleSheet(f"color: {TEXT_PRI}; font-size: 18px; font-weight: 800;")
        header_col.addWidget(header)
        sub = QLabel("xray-core runtime output and application events")
        sub.setStyleSheet(f"color: {TEXT_DIM}; font-size: 10px;")
        header_col.addWidget(sub)
        header_row.addLayout(header_col)
        header_row.addStretch()
        btn_clear = QPushButton("Clear")
        btn_clear.setCursor(Qt.PointingHandCursor)
        btn_clear.setStyleSheet(ghost_btn_qss(padding="6px 14px"))
        btn_clear.clicked.connect(self._clear_logs)
        header_row.addWidget(btn_clear)
        btn_copy = QPushButton("Copy")
        btn_copy.setCursor(Qt.PointingHandCursor)
        btn_copy.setStyleSheet(ghost_btn_qss(padding="6px 14px"))
        btn_copy.clicked.connect(self._copy_logs)
        header_row.addWidget(btn_copy)
        self.log_filter_combo = QComboBox()
        self.log_filter_combo.addItems(["All levels", "Info + warnings", "Warnings + errors", "Errors only"])
        self.log_filter_combo.setCursor(Qt.PointingHandCursor)
        self.log_filter_combo.setStyleSheet(
            f"QComboBox {{ background: {theme.current['MENU_BG']}; color: {TEXT_PRI}; "
            f"border: 1px solid {BORDER}; border-radius: 8px; padding: 6px 12px; "
            f"font-size: 11px; }}"
            f"QComboBox QAbstractItemView {{ background: {theme.current['MENU_BG']}; "
            f"color: {TEXT_PRI}; selection-background-color: {ACCENT}; border: none; }}"
        )
        self.log_filter_combo.currentIndexChanged.connect(self._on_log_filter_changed)
        header_row.addWidget(self.log_filter_combo)
        layout.addLayout(header_row)

        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumBlockCount(1000)
        self.log_view.setStyleSheet(
            f"QPlainTextEdit {{ background: {theme.current['MENU_BG']}; "
            f"color: {TEXT_SEC}; border: 1px solid {BORDER}; border-radius: 12px; "
            f"font-family: Consolas; font-size: 10.5px; padding: 10px; }}"
        )
        layout.addWidget(self.log_view, 1)
        return page

    def _log_line(self, text, level="INFO"):
        rank = {"DEBUG": 5, "INFO": 10, "WARN": 20, "ERROR": 30}.get(level, 10)
        if rank < getattr(self, "_log_min_rank", 5):
            return
        ts = time.strftime("%H:%M:%S")
        line = f"[{ts}] [{level}] {text}"
        self._log_lines.append(line)
        file_log(text, level)
        view = getattr(self, "log_view", None)
        if view is not None:
            view.appendPlainText(line)
            sb = view.verticalScrollBar()
            sb.setValue(sb.maximum())

    def _on_xray_log(self, text):
        self._log_line(text, "XRAY")

    def _on_log_filter_changed(self, index):
        self._log_min_rank = [5, 10, 20, 30][index]
        view = getattr(self, "log_view", None)
        if view is None:
            return
        view.clear()
        rank_of = {"DEBUG": 5, "INFO": 10, "WARN": 20, "ERROR": 30}
        for line in self._log_lines:
            level = "INFO"
            try:
                level = line.split("] [", 1)[1].rsplit("]", 1)[0]
            except IndexError:
                pass
            if rank_of.get(level, 10) >= self._log_min_rank:
                view.appendPlainText(line)

    def _clear_logs(self):
        self.log_view.clear()
        self._show_toast("Logs cleared", "success")

    def _copy_logs(self):
        QApplication.clipboard().setText("\n".join(self._log_lines))
        self._show_toast("Logs copied to clipboard", "success")

    # ---------- tray & shortcuts ----------

    def _make_tray_icon(self):
        pm = QPixmap(64, 64)
        pm.fill(Qt.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.Antialiasing)
        grad = QLinearGradient(0, 0, 64, 64)
        grad.setColorAt(0.0, QColor(theme.current["ACCENT"]))
        grad.setColorAt(1.0, QColor(theme.current["ACCENT_LIGHT"]))
        p.setPen(Qt.NoPen)
        p.setBrush(grad)
        p.drawRoundedRect(QRectF(4, 4, 56, 56), 15, 15)
        font = QFont("Segoe UI")
        font.setPixelSize(26)
        font.setBold(True)
        p.setFont(font)
        p.setPen(QColor("#FFFFFF"))
        p.drawText(QRectF(4, 4, 56, 56), Qt.AlignCenter, "Z")
        p.end()
        return QIcon(pm)

    def _setup_tray(self):
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return None
        tray = QSystemTrayIcon(self._make_tray_icon(), self)
        tray.setToolTip("Zify client")
        menu = QMenu()
        self.tray_menu_status = QAction("Disconnected", menu)
        self.tray_menu_status.setEnabled(False)
        self.tray_menu_toggle = QAction("Connect", menu)
        self.tray_menu_toggle.triggered.connect(self.toggle_connection)
        menu.addAction(self.tray_menu_status)
        menu.addAction(self.tray_menu_toggle)
        menu.addSeparator()
        act_show = QAction("Show Window", menu)
        act_show.triggered.connect(self._show_window)
        act_quit = QAction("Exit", menu)
        act_quit.triggered.connect(self._quit_app)
        menu.addAction(act_show)
        menu.addAction(act_quit)
        tray.setContextMenu(menu)
        tray.activated.connect(self._on_tray_activated)
        tray.show()
        return tray

    def _update_tray(self):
        tray = getattr(self, "tray", None)
        if tray is None or not hasattr(self, "connect_btn"):
            return
        state = self.connect_btn.state()
        if state is ConnectState.CONNECTED:
            self.tray_menu_status.setText("\u25CF Connected")
            self.tray_menu_toggle.setText("Disconnect")
            self.tray_menu_toggle.setEnabled(True)
            tray.setToolTip("Zify client \u2014 Connected")
        elif state is ConnectState.CONNECTING:
            self.tray_menu_status.setText("\u2026 Connecting")
            self.tray_menu_toggle.setText("Connecting\u2026")
            self.tray_menu_toggle.setEnabled(False)
            tray.setToolTip("Zify client \u2014 Connecting")
        else:
            self.tray_menu_status.setText("\u25CB Disconnected")
            self.tray_menu_toggle.setText("Connect")
            self.tray_menu_toggle.setEnabled(True)
            tray.setToolTip("Zify client")

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.Trigger:
            if self.isVisible():
                self.hide()
            else:
                self._show_window()

    def _show_window(self):
        self.show()
        self.raise_()
        self.activateWindow()

    def _quit_app(self):
        self._quitting = True
        if getattr(self, "tray", None) is not None:
            self.tray.hide()
        self.close()

    def _setup_shortcuts(self):
        self._shortcut_connect = QShortcut(QKeySequence("Ctrl+Q"), self)
        self._shortcut_connect.activated.connect(self.toggle_connection)
        self._shortcut_search = QShortcut(QKeySequence("Ctrl+F"), self)
        self._shortcut_search.activated.connect(self._focus_search)

    def _focus_search(self):
        self._switch_page(0)
        self.filter_search.setFocus()
        self.filter_search.selectAll()

    def _ping_spin_tick(self):
        if not self._ping_pending:
            self._ping_spin_timer.stop()
            return
        self._ping_frame += 1
        dots = ["\u00B7", "\u00B7\u00B7", "\u00B7\u00B7\u00B7"][self._ping_frame % 3]
        for pi, ni in list(self._ping_pending):
            for labels in (self._lat_labels, self._lat_labels_pick):
                lbl = labels.get((pi, ni))
                if lbl is not None:
                    lbl.setText(dots)
                    lbl.setStyleSheet(
                        f"color: {ACCENT_LIGHT}; font-size: 11px; font-weight: bold;"
                    )

    def _on_theme_changed(self, index):
        name = self.theme_combo.itemData(index)
        if not name or name == theme.current_name:
            return
        theme.apply(name)
        _bind_theme_globals()
        self._rebuild_after_theme()
        self._show_toast(f"Theme changed to {theme.DISPLAY.get(name, name)}", "success")

    def _rebuild_after_theme(self):
        cur = self.stack.currentIndex()
        for w in (self.sidebar_widget, self.stack):
            self.body_layout.removeWidget(w)
            w.deleteLater()

        self.sidebar_widget = self._build_sidebar()
        self.stack = QStackedWidget()
        self.body_layout.addWidget(self.sidebar_widget)
        self.body_layout.addWidget(self.stack, 1)

        self.page_connection = self._build_connection_page()
        self.page_servers = self._build_servers_page()
        self.page_settings = self._build_settings_page()
        self.page_logs = self._build_logs_page()
        self.stack.addWidget(self.page_connection)
        self.stack.addWidget(self.page_servers)
        self.stack.addWidget(self.page_settings)
        self.stack.addWidget(self.page_logs)
        self.stack.setCurrentIndex(cur)

        self._set_nav_active(cur)
        self.setStyleSheet(GLOBAL_QSS())
        self.title_bar.apply_theme()

        self._apply_settings_values()
        self._restore_theme_sticky_state()
        self._save_state()
        
        # Rebuild split tunnel UI
        if hasattr(self, "_split_apps"):
            self._rebuild_split_apps()
        # Rebuild killswitch UI
        if hasattr(self, "_killswitch_apps"):
            self._rebuild_killswitch_apps()
        # Rebuild routing domains UI
        if hasattr(self, "_routing_domains"):
            self._rebuild_routing_domains()
        # Rebuild DNS UI
        if hasattr(self, "_dns_config"):
            dns_id = self._dns_config.get("dns", "system")
            idx = self.dns_combo.findData(dns_id)
            self.dns_combo.setCurrentIndex(idx if idx >= 0 else 0)
            self._on_dns_changed(idx)
        # Rebuild IPv6 UI
        if hasattr(self, "_ipv6_config"):
            self.cb_ipv6_enabled.setChecked(self._ipv6_config.get("enabled", True))
            self.cb_ipv6_dns.setChecked(self._ipv6_config.get("dns_v6", True))
            self.cb_ipv6_routing.setChecked(self._ipv6_config.get("routing_v6", True))
            self.cb_ipv6_prefer.setChecked(self._ipv6_config.get("prefer_v6", False))
        # Rebuild update UI
        if hasattr(self, "_update_config"):
            self.cb_auto_update.setChecked(self._update_config.get("auto_update", False))
        # Rebuild theme combo
        if hasattr(self, "theme_combo"):
            idx = self.theme_combo.findData(theme.current_name)
            self.theme_combo.setCurrentIndex(idx if idx >= 0 else 0)
        # Rebuild routing combo
        if hasattr(self, "routing_combo"):
            mode = self._settings_values.get("routing_mode", "all")
            idx = self.routing_combo.findData(mode)
            self.routing_combo.setCurrentIndex(idx if idx >= 0 else 0)
        # Rebuild split mode combo
        if hasattr(self, "split_mode_combo"):
            split_mode = self._settings_values.get("split_tunnel_mode", "exclude")
            idx = self.split_mode_combo.findData(split_mode)
            self.split_mode_combo.setCurrentIndex(idx if idx >= 0 else 0)
        # Rebuild blocker checkboxes
        if hasattr(self, "cb_block_ads"):
            self.cb_block_ads.setChecked(self._dns_config.get("block_ads", False))
        if hasattr(self, "cb_block_trackers"):
            self.cb_block_trackers.setChecked(self._dns_config.get("block_trackers", False))
        if hasattr(self, "cb_block_malware"):
            self.cb_block_malware.setChecked(self._dns_config.get("block_malware", False))
        # Rebuild custom DNS input
        if hasattr(self, "custom_dns_input"):
            self.custom_dns_input.setText(self._dns_config.get("custom_dns", ""))
        # Rebuild killswitch app input
        if hasattr(self, "killswitch_app_input"):
            self.killswitch_app_input.clear()
        # Rebuild split app input
        if hasattr(self, "split_app_input"):
            self.split_app_input.clear()
        # Rebuild update status
        if hasattr(self, "update_status"):
            self.update_status.setText("")
            self.btn_download_update.hide()
        # Rebuild update thread
        if hasattr(self, "update_thread"):
            self.update_thread.deleteLater()
        if hasattr(self, "download_thread"):
            self.download_thread.deleteLater()
        # Rebuild theme combo signal
        if hasattr(self, "theme_combo"):
            self.theme_combo.blockSignals(True)
            idx = self.theme_combo.findData(theme.current_name)
            self.theme_combo.setCurrentIndex(idx if idx >= 0 else 0)
            self.theme_combo.blockSignals(False)

    def _restore_theme_sticky_state(self):
        self._set_status(self._status_text, self._status_color)
        self._set_metric_status(self._metric_status_text, self._metric_status_color)
        if self._last_latency_ms is not None:
            self._set_latency_metric(self._last_latency_ms)
        self.metric_down.setText(self._last_down_text)
        self.metric_up.setText(self._last_up_text)
        self.graph_down_label.setText(self._last_down_text)
        self.graph_up_label.setText(self._last_up_text)
        self.graph_ping_label.setText(self._last_ping_text)
        self._set_session_text()
        if self.xray_thread is not None and self.xray_thread.isRunning():
            self.connect_btn.set_state(ConnectState.CONNECTED)
            self._set_traffic_active(True)

    # ---------- selection ----------

    def _select_provider(self, index, node_index=0):
        if index < 0 or index >= len(self.providers):
            return
        prev = self.selected_provider_index
        self.selected_provider_index = index
        prov = self.providers[index]
        nodes = prov.get("nodes", [])
        if nodes and 0 <= node_index < len(nodes):
            self.selected_node_index = node_index
        else:
            self.selected_node_index = 0 if nodes else -1
        self._configure_from_selection()
        self._rebuild_providers_ui()
        self._refresh_server_pick()
        if prev != index:
            self._refresh_servers_page()
            self._save_state()

    def _select_and_connect(self, pi, ni):
        self._select_node(pi, ni)
        if self.connect_btn.state() is ConnectState.CONNECTED:
            self.disconnect()
            QTimer.singleShot(800, self.toggle_connection)
        else:
            self.toggle_connection()

    def _select_node(self, pi, ni):
        if pi < 0 or pi >= len(self.providers):
            return
        prov = self.providers[pi]
        nodes = prov.get("nodes", [])
        if not nodes or ni < 0 or ni >= len(nodes):
            return
        self.selected_provider_index = pi
        self.selected_node_index = ni
        self._configure_from_selection()
        self._rebuild_providers_ui()
        self._refresh_server_pick()
        self._refresh_servers_page()
        self._save_state()
        node = nodes[ni]
        self._show_toast(
            f"Node selected: {node.get('host', '?')}:{node.get('port', '?')}", "success"
        )

    def _configure_from_selection(self):
        if self.selected_provider_index < 0:
            self.config_file = None
            self.metric_server.setText("Не выбран")
            return
        prov = self.providers[self.selected_provider_index]
        nodes = prov.get("nodes", [])
        idx = self.selected_node_index
        display = prov.get("host", "?")
        if nodes and 0 <= idx < len(nodes):
            node = nodes[idx]
            flag = node.get("_flag")
            country = node.get("_country")
            if flag is None:
                flag, country = detect_country(node)
                if flag is None:
                    flag, country = "\U0001F310", "Неизвестно"
                node["_flag"], node["_country"] = flag, country
            name = node.get("ps") or node.get("name") or country or node.get("host", "?")
            display = f"{flag} {name}"
        self.config_file = prov.get("config_file")
        self.metric_server.setText(display)

    def show_add_config_dialog(self):
        dialog = AddConfigDialog(self)
        if dialog.exec() == QDialog.Accepted:
            config_url = dialog.get_config_url()
            if not config_url:
                self._show_toast("Config URL is required", "error")
                return
            try:
                parsed = parse_config(config_url)
                host = parsed.get("host", "Unknown")
                proto = parsed.get("type", "vmess").upper()
                sub_url = parsed.get("subscription_url", "")
                fd, cfg_path = tempfile.mkstemp(suffix=".json", prefix="vpn_")
                os.close(fd)
                if sub_url:
                    display_name = parse_url(sub_url).hostname or host
                    node = {"host": host, "port": parsed.get("port", 443),
                            "type": parsed.get("type", "vmess"), "_loading": True}
                    provider = {
                        "host": display_name,
                        "type": "SUB",
                        "url": config_url,
                        "parsed": parsed,
                        "nodes": [node],
                        "config_file": cfg_path,
                        "_subscription_url": sub_url,
                    }
                    self.providers.append(provider)
                    pi = len(self.providers) - 1
                    self._select_provider(pi, 0)
                    self._set_status("Configured", YELLOW)
                    self._save_state()
                    self._show_toast("Loading subscription in background...", "warning")

                    fetcher = SubFetchThread(config_url)
                    fetcher.nodes_ready.connect(
                        lambda nodes, p=pi: self._on_subscription_nodes(p, nodes)
                    )
                    fetcher.error.connect(
                        lambda err, p=pi: self._on_subscription_error(p, err)
                    )
                    self._loading_subscriptions[pi] = fetcher
                    fetcher.start()
                else:
                    display_name = host
                    all_nodes = [parsed]
                    provider = {
                        "host": display_name,
                        "type": proto,
                        "url": config_url,
                        "parsed": parsed,
                        "nodes": all_nodes,
                        "config_file": cfg_path,
                    }
                    self.providers.append(provider)
                    self._select_provider(len(self.providers) - 1, 0)
                    self._set_status("Configured", YELLOW)
                    self._save_state()
                    self._show_toast("Provider saved for next sessions", "success")
            except Exception as e:
                self._show_toast(f"Failed: {e}", "error")

    # ---------- connection flow ----------

    def toggle_connection(self):
        state = self.connect_btn.state()
        if state is ConnectState.CONNECTED:
            self.disconnect()
            return
        if state is ConnectState.CONNECTING:
            return
        if self.config_file is None:
            self.connect_btn.shake()
            self._show_toast("Add a configuration first", "error")
            return
        self._start_connection()

    def _start_connection(self):
        self.connect_btn.bounce()
        self.connect_btn.set_state(ConnectState.CONNECTING)
        self._set_status("Connecting...", YELLOW)
        self._set_metric_status("Connecting...", YELLOW)
        self._set_glow(True)
        self._log_line("Starting connection\u2026", "VPN")

        node_data = None
        if self.selected_provider_index >= 0:
            prov = self.providers[self.selected_provider_index]
            nodes = prov.get("nodes", [])
            idx = self.selected_node_index
            if nodes and 0 <= idx < len(nodes):
                node_data = nodes[idx]
            else:
                node_data = prov.get("parsed")

        routing = {
            "mode": self.routing_combo.currentData() or "all",
            "custom_domains": list(self._routing_domains),
        }
        tun_mode = bool(self.cb_tun_mode.isChecked())
        if tun_mode and not _is_admin():
            tun_mode = False
            self._log_line("TUN mode disabled — requires admin rights, using proxy instead", "TUN")
            self._show_toast("TUN mode needs admin — using proxy instead", "warning")
        self.xray_thread = XRayThread(self.config_file, node_data, routing, tun_mode=tun_mode)
        self.xray_thread.success.connect(self.on_connected)
        self.xray_thread.error.connect(self.on_connection_error)
        self.xray_thread.log_line.connect(self._on_xray_log)
        self.xray_thread.start()

        self.stats_thread = TrafficStats()
        self.stats_thread.update_traffic.connect(self.update_stats)
        self.stats_thread.start()

        self.ping_timer.start()

    def on_connected(self, msg):
        self._smart_retries = 0
        self.connect_btn.set_state(ConnectState.CONNECTED)
        self._set_status("Verifying tunnel\u2026", YELLOW)
        self._set_metric_status("Verifying\u2026", YELLOW)
        self._set_traffic_active(True)
        self._log_line(f"Tunnel active: {msg}", "VPN")
        self._show_toast("Tunnel active \u2014 verifying\u2026", "warning")
        self._schedule_health_check(repeat=True)
        if self.cb_killswitch.isChecked():
            if killswitch_enable():
                self._killswitch_active = True
                self._log_line("Kill switch engaged", "KS")
            else:
                self._show_toast("Kill switch needs admin rights", "error")
        if self.cb_system_proxy.isChecked():
            if set_system_proxy(True):
                self._sys_proxy_active = True
            else:
                self._show_toast("Failed to enable system proxy", "error")
        if self.tray is not None and self.cb_notifications.isChecked():
            self.tray.showMessage(
                "Zify client", "Tunnel active", QSystemTrayIcon.Information, 2500
            )

    # ---------- tunnel health check ----------

    def _schedule_health_check(self, delay=1500, repeat=False):
        if self._health_thread is not None:
            return
        QTimer.singleShot(delay, self._run_health_check)
        if repeat:
            self._health_interval_timer = QTimer(self)
            self._health_interval_timer.setInterval(30000)
            self._health_interval_timer.timeout.connect(self._run_health_check)
            self._health_interval_timer.start()

    def _run_health_check(self):
        if self._health_thread is not None:
            return
        self._health_status = "checking"
        self._health_thread = HealthCheckThread()
        self._health_thread.done.connect(self._on_health_done)
        self._health_thread.start()

    def _on_health_done(self, info, ok):
        self._health_thread = None
        self._health_status = "up" if ok else "down"
        if ok:
            self._last_check_ip = info
            self._set_status(f"Connected \u00b7 {info}", GREEN)
            self._set_metric_status("Connected", GREEN)
            self._log_line(f"Tunnel verified \u2014 exit IP {info}", "VPN")
        else:
            self._last_check_ip = None
            self._set_status("Connected? no traffic", YELLOW)
            self._set_metric_status("Connected?", YELLOW)
            self._log_line(f"Health check failed: {info}", "VPN")
            self._show_toast("Tunnel may be down \u2014 checking again\u2026", "warning")

    def on_connection_error(self, err):
        self._teardown_connection_threads()
        self.connect_btn.set_state(ConnectState.IDLE)
        self.connect_btn.shake()
        self._set_status("Disconnected", RED)
        self._set_metric_status("Disconnected", RED)
        self._set_traffic_active(False)
        self._set_glow(False)
        self.ping_timer.stop()
        if self._sys_proxy_active:
            self._sys_proxy_active = False
            set_system_proxy(False)
        self._log_line(f"Connection error: {err}", "VPN")
        self._show_toast(f"Failed to start tunnel: {err}", "error")
        if self._killswitch_active:
            self._log_line("Kill switch stays active \u2014 traffic blocked until reconnect", "KS")
        if self.cb_smart_connect.isChecked() and self._smart_retries < 3:
            self._smart_retries += 1
            self._show_toast(
                f"Reconnecting \u2014 attempt {self._smart_retries}/3\u2026", "warning"
            )
            QTimer.singleShot(1500, self._smart_reconnect)

    def _smart_reconnect(self):
        if self.connect_btn.state() is not ConnectState.IDLE:
            return
        self._fast_select(auto_connect=True)

    def disconnect(self):
        self._teardown_connection_threads()
        self.connect_btn.set_state(ConnectState.IDLE)
        self._set_traffic_active(False)
        self._set_glow(False)
        self.dl_graph.reset()
        self.ul_graph.reset()
        self.ping_graph.reset()
        self.session_down = 0.0
        self.session_up = 0.0
        self._set_session_text()

        self._set_status("Disconnected", RED)
        self._set_metric_status("Disconnected", RED)
        self.metric_latency.setText("-- ms")
        self.metric_latency.setStyleSheet(f"color: {TEXT_SEC}; font-size: 15px; font-weight: bold;")
        self._last_down_text = "0 B/s"
        self._last_up_text = "0 B/s"
        self.graph_down_label.setText("0 B/s")
        self.graph_up_label.setText("0 B/s")
        self.graph_ping_label.setText("\u2014 ms")
        self.ping_timer.stop()
        if self._sys_proxy_active:
            self._sys_proxy_active = False
            set_system_proxy(False)
        if self._killswitch_active:
            self._killswitch_active = False
            killswitch_disable()
            self._log_line("Kill switch released", "KS")
        self._log_line("Disconnected by user", "VPN")
        self._show_toast("Disconnected")
        if self.tray is not None and self.cb_notifications.isChecked():
            self.tray.showMessage(
                "Zify client", "Disconnected", QSystemTrayIcon.Information, 2000
            )

    def _teardown_connection_threads(self):
        if self.xray_thread:
            self.xray_thread.stop()
            self.xray_thread.wait(3000)
            self.xray_thread = None
        if self.stats_thread:
            self.stats_thread.stop()
            self.stats_thread = None
        if self._health_thread is not None:
            self._health_thread.terminate()
            self._health_thread = None
        self._health_status = None
        self._last_check_ip = None

    def update_stats(self, download, upload):
        self._last_down_text = self._format_speed(download)
        self._last_up_text = self._format_speed(upload)
        self.metric_down.setText(self._last_down_text)
        self.metric_up.setText(self._last_up_text)
        self.dl_graph.add_point(download, 0)
        self.ul_graph.add_point(0, upload)
        self.graph_down_label.setText(self._last_down_text)
        self.graph_up_label.setText(self._last_up_text)

        self.session_down += download
        self.session_up += upload
        self._set_session_text()

    # ---------- latency ----------

    def _thread_done(self, t):
        if t in self._latency_threads:
            self._latency_threads.remove(t)

    def _ping_single_node(self, pi, ni):
        try:
            node = self.providers[pi]["nodes"][ni]
        except (IndexError, KeyError):
            return
        host = node.get("host", "")
        port = node.get("port", 443)
        if not host:
            return
        t = LatencyTestThread(host, port, use_proxy=False)
        t.result.connect(lambda h, p, ms, pi=pi, ni=ni: self._ping_node_result(pi, ni, ms))
        t.finished.connect(lambda: self._thread_done(t))
        self._latency_threads.append(t)
        t.start()

    def _ping_node_result(self, pi, ni, ms):
        try:
            node = self.providers[pi]["nodes"][ni]
        except (IndexError, KeyError):
            return
        node["_latency"] = ms
        self._ping_pending.discard((pi, ni))
        self._update_latency_label(pi, ni, ms)
        if pi == self.selected_provider_index and ni == self.selected_node_index:
            self._set_latency_metric(ms)
            if ms >= 0:
                self._last_ping_text = f"{ms} ms"
                self.ping_graph.add_value(ms)
                self.graph_ping_label.setText(self._last_ping_text)

    def _update_latency_label(self, pi, ni, ms):
        for labels in (self._lat_labels, self._lat_labels_pick):
            lbl = labels.get((pi, ni))
            if lbl is None:
                continue
            if ms < 0:
                lbl.setText("Timeout")
                lbl.setStyleSheet(f"color: {RED}; font-size: 11px; font-weight: bold;")
            else:
                c = GREEN if ms < 100 else (YELLOW if ms < 250 else RED)
                lbl.setText(f"{ms} ms")
                lbl.setStyleSheet(f"color: {c}; font-size: 11px; font-weight: bold;")

    def _set_latency_metric(self, ms):
        self._last_latency_ms = ms
        if ms < 0:
            self.metric_latency.setText("Timeout")
            self.metric_latency.setStyleSheet(f"color: {RED}; font-size: 15px; font-weight: bold;")
        else:
            self.metric_latency.setText(f"{ms} ms")
            c = GREEN if ms < 50 else (YELLOW if ms < 150 else RED)
            self.metric_latency.setStyleSheet(f"color: {c}; font-size: 15px; font-weight: bold;")

    def _quick_ping(self):
        if self.selected_provider_index < 0 or self.selected_node_index < 0:
            return
        try:
            node = self.providers[self.selected_provider_index]["nodes"][self.selected_node_index]
        except (IndexError, KeyError):
            return
        host = node.get("host", "")
        port = node.get("port", 443)
        if not host:
            return
        t = LatencyTestThread(host, port, use_proxy=False)
        t.result.connect(self._quick_ping_result)
        t.finished.connect(lambda: self._thread_done(t))
        self._latency_threads.append(t)
        t.start()

    def _quick_ping_result(self, host_, port_, ms):
        self._set_latency_metric(ms)
        if ms >= 0:
            self._last_ping_text = f"{ms} ms"
            self.ping_graph.add_value(ms)
            self.graph_ping_label.setText(self._last_ping_text)

    def _ping_all_servers(self):
        targets = []
        for pi, prov in enumerate(self.providers):
            for ni, node in enumerate(prov.get("nodes", [])):
                host = node.get("host", "")
                port = node.get("port", 443)
                if host:
                    targets.append((pi, ni, host, port))
        if not targets:
            self._show_toast("No nodes to ping", "error")
            return
        self.btn_ping_all.setText("Измеряю…")
        self.btn_ping_all.setEnabled(False)
        self._log_line(f"Measuring TCP latency of {len(targets)} nodes", "PING")
        self._ping_pending = {(pi, ni) for pi, ni, _, _ in targets}
        self._ping_spin_timer.start()
        for pi, ni, host, port in targets:
            t = LatencyTestThread(host, port, use_proxy=False)
            t.result.connect(lambda h, p, ms, pi=pi, ni=ni: self._ping_node_result(pi, ni, ms))
            t.finished.connect(lambda: self._thread_done(t))
            self._latency_threads.append(t)
            t.start()
        QTimer.singleShot(4000, self._finalize_ping_all)

    def _finalize_ping_all(self):
        self.btn_ping_all.setText("Пинг")
        self.btn_ping_all.setEnabled(True)
        self._ping_pending.clear()
        self._ping_spin_timer.stop()
        self._log_line("Latency test finished", "PING")
        self._show_toast("Замер задержки завершён", "success")

    def _show_qr(self, pi, ni):
        try:
            node = self.providers[pi]["nodes"][ni]
        except (IndexError, KeyError):
            return
        raw_url = node.get("raw_url", "")
        if not raw_url:
            self._show_toast("No shareable link for this node", "error")
            return
        host = node.get("host", "?")
        dlg = QRDialog(raw_url, host, self)
        dlg.exec()

    def _fast_select(self, auto_connect=False):
        self._fastest_results = {}
        self._fast_select_autoconnect = auto_connect
        pending = 0
        for pi, prov in enumerate(self.providers):
            for ni, node in enumerate(prov.get("nodes", [])):
                host = node.get("host", "")
                port = node.get("port", 443)
                if not host:
                    continue
                pending += 1
                self._ping_pending.add((pi, ni))
                t = LatencyTestThread(host, port, use_proxy=False)
                t.result.connect(
                    lambda h, p, ms, pi=pi, ni=ni: self._on_fast_select(pi, ni, ms)
                )
                t.finished.connect(lambda: self._thread_done(t))
                self._latency_threads.append(t)
                t.start()
        self._ping_spin_timer.start()
        if pending == 0:
            self._ping_pending.clear()
            self._ping_spin_timer.stop()
            self._show_toast("No nodes to scan. Add a provider first.", "error")
            return
        self._show_toast(f"Scanning {pending} nodes for the fastest server...", "warning")
        QTimer.singleShot(4000, self._finish_fast_select)

    def _on_fast_select(self, pi, ni, ms):
        self._fastest_results[(pi, ni)] = ms
        self._ping_pending.discard((pi, ni))

    def _finish_fast_select(self):
        self._ping_pending.clear()
        self._ping_spin_timer.stop()
        if not self._fastest_results:
            self._show_toast("No latency results available", "error")
            return
        for (kpi, kni), v in self._fastest_results.items():
            try:
                self.providers[kpi]["nodes"][kni]["_latency"] = v
            except (IndexError, KeyError):
                pass
            self._update_latency_label(kpi, kni, v)
        best = min(
            self._fastest_results.items(),
            key=lambda kv: kv[1] if kv[1] >= 0 else 999999
        )
        (pi, ni), ms = best
        self._select_node(pi, ni)
        self._set_latency_metric(ms)
        self._log_line(f"Fastest node selected: {ms} ms", "SMART")
        if self._fast_select_autoconnect and self.connect_btn.state() is ConnectState.IDLE:
            self._show_toast(f"Fastest node {ms} ms \u2014 connecting\u2026", "warning")
            self.toggle_connection()
        else:
            self._show_toast(f"Fastest node selected: {ms} ms", "success")

    # ---------- session & helpers ----------

    def _reset_session(self):
        self.session_down = 0.0
        self.session_up = 0.0
        self._set_session_text()
        self.dl_graph.reset()
        self.ul_graph.reset()
        self.ping_graph.reset()
        self._show_toast("Session counter reset", "success")

    def closeEvent(self, event):
        if not self._quitting and getattr(self, "tray", None) is not None:
            event.ignore()
            self.hide()
            if self.cb_notifications.isChecked():
                self.tray.showMessage(
                    "Zify client", "Still running in the system tray",
                    QSystemTrayIcon.Information, 2500,
                )
            return
        self._save_state()
        self._set_glow(False)
        self.ping_timer.stop()
        if self._sys_proxy_active:
            self._sys_proxy_active = False
            set_system_proxy(False)
        if self._killswitch_active:
            self._killswitch_active = False
            killswitch_disable()
        self._teardown_connection_threads()
        for t in list(self._latency_threads):
            try:
                t.wait(500)
            except Exception:
                pass
        self._cleanup_temp_files()
        self._log_line("Application closed", "APP")
        super().closeEvent(event)

    def _cleanup_temp_files(self):
        for prov in self.providers:
            cfg = prov.get("config_file")
            if cfg and os.path.isfile(cfg):
                try:
                    os.unlink(cfg)
                except Exception:
                    pass

    def _run_speedtest(self, pi, ni):
        try:
            node = self.providers[pi]["nodes"][ni]
        except (IndexError, KeyError):
            return
        self._show_toast("Speed test started\u2026", "warning")
        self._speedtest_thread = SpeedTestThread()
        self._speedtest_thread.result.connect(
            lambda mbps, lat: self._on_speedtest_result(pi, ni, mbps, lat)
        )
        self._speedtest_thread.error.connect(lambda err: self._show_toast(err, "error"))
        self._speedtest_thread.start()

    def _on_speedtest_result(self, pi, ni, mbps, lat):
        node = self.providers[pi]["nodes"][ni] if 0 <= pi < len(self.providers) and 0 <= ni < len(self.providers[pi].get("nodes", [])) else None
        if node:
            node["_speed_mbps"] = mbps
            node["_latency"] = int(lat) if lat >= 0 else None
            self._update_latency_label(pi, ni, int(lat) if lat >= 0 else -1)
            self._save_state()
        lat_str = f"{lat:.0f} ms" if lat >= 0 else "Timeout"
        self._show_toast(f"Speed: {mbps:.1f} Mbps, Latency: {lat_str}", "success")
        self._log_line(f"Speed test: {mbps:.1f} Mbps, {lat_str}", "SPEED")

    def _format_speed(self, value):
        """value is bytes/s from xray gRPC stats."""
        if value >= 1024 ** 3:
            return f"{value / 1024 ** 3:.1f} GB/s"
        if value >= 1024 ** 2:
            return f"{value / 1024 ** 2:.1f} MB/s"
        if value >= 1024:
            return f"{value / 1024:.1f} KB/s"
        return f"{int(value)} B/s"

    # NOTE: value is already in KB/s from TrafficStats
    # GB/s threshold is correct: 1024*1024 KB/s = 1 GB/s

    def _format_size(self, bytes_val):
        if bytes_val >= 1024 * 1024 * 1024:
            return f"{bytes_val / (1024 * 1024 * 1024):.1f} GB"
        if bytes_val >= 1024 * 1024:
            return f"{bytes_val / (1024 * 1024):.1f} MB"
        if bytes_val >= 1024:
            return f"{bytes_val / 1024:.1f} KB"
        return f"{int(bytes_val)} B"

    def _show_toast(self, message, kind="success"):
        self.toast.notify(message, kind)
