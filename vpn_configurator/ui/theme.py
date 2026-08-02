from PySide6.QtGui import QColor

DEFAULT_NAME = "ultra_black"

DISPLAY = {
    "ultra_black": "Ultra Black",
    "midnight_violet": "Midnight Violet",
    "aurora": "Aurora",
    "ember": "Ember",
    "rose": "Rose",
}

THEMES = {
    "ultra_black": {
        "BG": "#07070B",
        "SIDEBAR_BG": "rgba(255,255,255,0.02)",
        "CARD": "rgba(255,255,255,0.03)",
        "CARD_HOVER": "rgba(255,255,255,0.055)",
        "CARD_ACTIVE": "rgba(108,92,231,0.12)",
        "BORDER": "rgba(255,255,255,0.08)",
        "BORDER_HOVER": "rgba(255,255,255,0.17)",
        "ACCENT": "#6C5CE7",
        "ACCENT_LIGHT": "#9B8CFF",
        "TEXT_PRI": "#F2F4FA",
        "TEXT_SEC": "#9AA3B8",
        "TEXT_DIM": "#5F6A85",
        "GREEN": "#00FF87",
        "YELLOW": "#FFC048",
        "RED": "#FF6B81",
        "CYAN": "#00D9F5",
        "GRAD_CONNECT": "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00E59A, stop:1 #00B8FF)",
        "GRAD_DISCONNECT": "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #FF6B81, stop:1 #FF9A62)",
        "GRAD_ACCENT": "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #6C5CE7, stop:1 #8B7CFF)",
        "GLOW1": "#6C5CE7",
        "GLOW1_ALPHA": 26,
        "GLOW2": "#00D9F5",
        "GLOW2_ALPHA": 15,
        "GLOW_CONNECT": "#00E59A",
        "MENU_BG": "#12141E",
        "DIALOG_BG": "#10131C",
        "TOAST_BG": "rgba(16,18,28,0.94)",
    },
    "midnight_violet": {
        "BG": "#0A0812",
        "SIDEBAR_BG": "rgba(255,255,255,0.02)",
        "CARD": "rgba(255,255,255,0.03)",
        "CARD_HOVER": "rgba(255,255,255,0.055)",
        "CARD_ACTIVE": "rgba(139,92,246,0.14)",
        "BORDER": "rgba(196,181,253,0.10)",
        "BORDER_HOVER": "rgba(196,181,253,0.22)",
        "ACCENT": "#8B5CF6",
        "ACCENT_LIGHT": "#C4B5FD",
        "TEXT_PRI": "#F4F1FF",
        "TEXT_SEC": "#A69FC0",
        "TEXT_DIM": "#6E6790",
        "GREEN": "#34F5C5",
        "YELLOW": "#FBBF24",
        "RED": "#FB7185",
        "CYAN": "#22D3EE",
        "GRAD_CONNECT": "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #8B5CF6, stop:1 #D946EF)",
        "GRAD_DISCONNECT": "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #FB7185, stop:1 #F97316)",
        "GRAD_ACCENT": "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #8B5CF6, stop:1 #A78BFA)",
        "GLOW1": "#8B5CF6",
        "GLOW1_ALPHA": 30,
        "GLOW2": "#D946EF",
        "GLOW2_ALPHA": 14,
        "GLOW_CONNECT": "#8B5CF6",
        "MENU_BG": "#150F26",
        "DIALOG_BG": "#140E24",
        "TOAST_BG": "rgba(21,15,38,0.94)",
    },
    "aurora": {
        "BG": "#06100E",
        "SIDEBAR_BG": "rgba(255,255,255,0.02)",
        "CARD": "rgba(255,255,255,0.03)",
        "CARD_HOVER": "rgba(255,255,255,0.055)",
        "CARD_ACTIVE": "rgba(0,229,160,0.10)",
        "BORDER": "rgba(120,242,204,0.10)",
        "BORDER_HOVER": "rgba(120,242,204,0.22)",
        "ACCENT": "#00E5A0",
        "ACCENT_LIGHT": "#6AF2C9",
        "TEXT_PRI": "#EFFFFA",
        "TEXT_SEC": "#8FB3AC",
        "TEXT_DIM": "#4F756E",
        "GREEN": "#7DFAD4",
        "YELLOW": "#FFD166",
        "RED": "#FF6B6B",
        "CYAN": "#48CFFF",
        "GRAD_CONNECT": "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00E5A0, stop:1 #00C2FF)",
        "GRAD_DISCONNECT": "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #FF6B6B, stop:1 #FF9F43)",
        "GRAD_ACCENT": "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00E5A0, stop:1 #00C2FF)",
        "GLOW1": "#00E5A0",
        "GLOW1_ALPHA": 20,
        "GLOW2": "#00C2FF",
        "GLOW2_ALPHA": 14,
        "GLOW_CONNECT": "#00E5A0",
        "MENU_BG": "#0C1B18",
        "DIALOG_BG": "#0B1715",
        "TOAST_BG": "rgba(12,27,24,0.94)",
    },
    "ember": {
        "BG": "#120B07",
        "SIDEBAR_BG": "rgba(255,255,255,0.02)",
        "CARD": "rgba(255,255,255,0.03)",
        "CARD_HOVER": "rgba(255,255,255,0.055)",
        "CARD_ACTIVE": "rgba(255,159,67,0.12)",
        "BORDER": "rgba(255,192,120,0.10)",
        "BORDER_HOVER": "rgba(255,192,120,0.22)",
        "ACCENT": "#FF9F43",
        "ACCENT_LIGHT": "#FFC078",
        "TEXT_PRI": "#FFF7EF",
        "TEXT_SEC": "#B8A394",
        "TEXT_DIM": "#7A6A58",
        "GREEN": "#7CFFB2",
        "YELLOW": "#FFD166",
        "RED": "#FF6B6B",
        "CYAN": "#5CE1E6",
        "GRAD_CONNECT": "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #FF9F43, stop:1 #FFD166)",
        "GRAD_DISCONNECT": "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #FF6B6B, stop:1 #FF9F43)",
        "GRAD_ACCENT": "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #FF9F43, stop:1 #FFC078)",
        "GLOW1": "#FF9F43",
        "GLOW1_ALPHA": 20,
        "GLOW2": "#FF6B6B",
        "GLOW2_ALPHA": 12,
        "GLOW_CONNECT": "#00E59A",
        "MENU_BG": "#1A120B",
        "DIALOG_BG": "#170F09",
        "TOAST_BG": "rgba(26,18,11,0.94)",
    },
    "rose": {
        "BG": "#120910",
        "SIDEBAR_BG": "rgba(255,255,255,0.02)",
        "CARD": "rgba(255,255,255,0.03)",
        "CARD_HOVER": "rgba(255,255,255,0.055)",
        "CARD_ACTIVE": "rgba(236,72,153,0.13)",
        "BORDER": "rgba(249,168,212,0.10)",
        "BORDER_HOVER": "rgba(249,168,212,0.22)",
        "ACCENT": "#EC4899",
        "ACCENT_LIGHT": "#F9A8D4",
        "TEXT_PRI": "#FFF4FA",
        "TEXT_SEC": "#B89AB0",
        "TEXT_DIM": "#7A5F74",
        "GREEN": "#5EEAD4",
        "YELLOW": "#FCD34D",
        "RED": "#FB7185",
        "CYAN": "#67E8F9",
        "GRAD_CONNECT": "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #EC4899, stop:1 #A78BFA)",
        "GRAD_DISCONNECT": "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #FB7185, stop:1 #FF9F43)",
        "GRAD_ACCENT": "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #EC4899, stop:1 #A78BFA)",
        "GLOW1": "#EC4899",
        "GLOW1_ALPHA": 22,
        "GLOW2": "#A78BFA",
        "GLOW2_ALPHA": 14,
        "GLOW_CONNECT": "#00E59A",
        "MENU_BG": "#1D0F18",
        "DIALOG_BG": "#1B0E16",
        "TOAST_BG": "rgba(29,15,24,0.94)",
    },
}

current_name = DEFAULT_NAME
current = dict(THEMES[DEFAULT_NAME])


def names():
    return list(THEMES.keys())


def apply(name):
    global current_name, current
    if name not in THEMES:
        name = DEFAULT_NAME
    current_name = name
    current.clear()
    current.update(THEMES[name])


def hex_rgba(hex_color, alpha):
    c = QColor(hex_color)
    return f"rgba({c.red()},{c.green()},{c.blue()},{alpha})"


def card_qss(selector="#card", radius=14, hover=True):
    s = (
        f"{selector} {{ background: {current['CARD']}; border: 1px solid {current['BORDER']}; "
        f"border-radius: {radius}px; }}"
    )
    if hover:
        s += (
            f"{selector}:hover {{ background: {current['CARD_HOVER']}; "
            f"border: 1px solid {current['BORDER_HOVER']}; }}"
        )
    return s


def ghost_btn_qss(color=None, radius=8, padding="6px 14px", font_size=11):
    color = color or current["ACCENT"]
    return (
        f"QPushButton {{ background: transparent; color: {color}; "
        f"border: 1px solid {hex_rgba(color, 0.35)}; border-radius: {radius}px; "
        f"padding: {padding}; font-size: {font_size}px; font-weight: 600; }}"
        f"QPushButton:hover {{ background: {hex_rgba(color, 0.12)}; "
        f"border: 1px solid {hex_rgba(color, 0.6)}; }}"
        f"QPushButton:pressed {{ background: {hex_rgba(color, 0.2)}; }}"
        f"QPushButton:disabled {{ color: {current['TEXT_DIM']}; "
        f"border-color: rgba(255,255,255,0.08); background: transparent; }}"
    )


def GLOBAL_QSS():
    return f"""
        QWidget {{
            border: none;
            background: transparent;
            color: {current['TEXT_SEC']};
            font-family: "Segoe UI";
        }}
        QLabel {{ color: {current['TEXT_SEC']}; }}
        QToolTip {{
            background-color: {current['MENU_BG']};
            color: {current['TEXT_PRI']};
            border: 1px solid rgba(255,255,255,0.12);
            padding: 6px 10px;
            border-radius: 6px;
            font-size: 11px;
        }}
        QScrollArea {{ background: transparent; border: none; }}
        QScrollArea > QWidget > QWidget {{ background: transparent; }}
        QScrollBar:vertical {{
            background: transparent; width: 9px; margin: 2px;
        }}
        QScrollBar::handle:vertical {{
            background: rgba(255,255,255,0.10); border-radius: 4px; min-height: 28px;
        }}
        QScrollBar::handle:vertical:hover {{ background: rgba(255,255,255,0.20); }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}
        QScrollBar:horizontal {{
            background: transparent; height: 6px; margin: 1px;
        }}
        QScrollBar::handle:horizontal {{
            background: rgba(255,255,255,0.10); border-radius: 3px; min-width: 30px;
        }}
        QScrollBar::handle:horizontal:hover {{ background: rgba(255,255,255,0.20); }}
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0px; }}
        QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{ background: transparent; }}
        QCheckBox {{ spacing: 12px; color: {current['TEXT_PRI']}; font-size: 13px; }}
        QCheckBox::indicator {{
            width: 46px; height: 24px; border-radius: 12px; border: none;
            background: rgba(255,255,255,0.08);
        }}
        QCheckBox::indicator:hover {{ background: rgba(255,255,255,0.14); }}
        QCheckBox::indicator:checked {{ background: {current['GRAD_ACCENT']}; }}
        QMenu {{
            background-color: {current['MENU_BG']};
            color: {current['TEXT_PRI']};
            border: 1px solid rgba(255,255,255,0.10);
            border-radius: 10px;
            padding: 6px;
            font-size: 12px;
        }}
        QMenu::item {{ padding: 7px 20px; border-radius: 6px; }}
        QMenu::item:selected {{ background: rgba(255,255,255,0.08); color: #FFFFFF; }}
        QMenu::separator {{ height: 1px; background: rgba(255,255,255,0.08); margin: 4px 10px; }}
        QComboBox {{
            background: {current['CARD']};
            color: {current['TEXT_PRI']};
            border: 1px solid {current['BORDER']};
            border-radius: 10px;
            padding: 8px 12px;
            font-size: 12px;
        }}
        QComboBox:hover {{ border: 1px solid {current['BORDER_HOVER']}; }}
        QComboBox::drop-down {{ border: none; width: 24px; }}
        QComboBox::down-arrow {{
            image: none;
            border-left: 5px solid transparent;
            border-right: 5px solid transparent;
            border-top: 6px solid {current['TEXT_SEC']};
        }}
        QComboBox QAbstractItemView {{
            background-color: {current['MENU_BG']};
            color: {current['TEXT_PRI']};
            border: 1px solid {current['BORDER']};
            border-radius: 8px;
            selection-background-color: rgba(255,255,255,0.08);
            padding: 4px;
            outline: none;
        }}
    """
