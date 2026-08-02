"""App Kill Switch — блокировка приложений при отключении VPN."""
import os
import sys
import subprocess
import json
from pathlib import Path


KILL_SWITCH_FILE = "killswitch_apps.json"


def get_killswitch_path():
    """Путь к файлу конфигурации kill switch."""
    base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    data_dir = os.path.join(base, "data")
    os.makedirs(data_dir, exist_ok=True)
    return os.path.join(data_dir, KILL_SWITCH_FILE)


def load_killswitch_apps():
    """Загрузить список приложений для kill switch."""
    path = get_killswitch_path()
    if not os.path.isfile(path):
        return {"enabled": False, "apps": []}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"enabled": False, "apps": []}


def save_killswitch_apps(data):
    """Сохранить список приложений."""
    path = get_killswitch_path()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def enable_killswitch_for_apps(apps):
    """Включить kill switch для указанных приложений."""
    if sys.platform != "win32":
        return False
    try:
        # Используем Windows Firewall для блокировки трафика
        for app_path in apps:
            exe_name = os.path.basename(app_path)
            rule_name = f"Zify_KillSwitch_{exe_name}"
            
            # Удаляем старое правило
            subprocess.run(
                ["netsh", "advfirewall", "firewall", "delete", "rule", f"name={rule_name}"],
                capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW
            )
            
            # Создаём новое правило — блокируем весь трафик
            subprocess.run(
                ["netsh", "advfirewall", "firewall", "add", "rule",
                 f"name={rule_name}",
                 "dir=out",
                 "action=block",
                 f"program={app_path}",
                 "profile=any"],
                capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW
            )
        return True
    except Exception:
        return False


def disable_killswitch_for_apps(apps):
    """Отключить kill switch для указанных приложений."""
    if sys.platform != "win32":
        return False
    try:
        for app_path in apps:
            exe_name = os.path.basename(app_path)
            rule_name = f"Zify_KillSwitch_{exe_name}"
            
            subprocess.run(
                ["netsh", "advfirewall", "firewall", "delete", "rule", f"name={rule_name}"],
                capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW
            )
        return True
    except Exception:
        return False


def enable_global_killswitch():
    """Глобальный kill switch — блокировка всего трафика кроме VPN."""
    if sys.platform != "win32":
        return False
    try:
        # Блокируем весь исходящий трафик
        subprocess.run(
            ["netsh", "advfirewall", "firewall", "set", "profile", "state", "on"],
            capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW
        )
        return True
    except Exception:
        return False


def disable_global_killswitch():
    """Отключить глобальный kill switch."""
    if sys.platform != "win32":
        return False
    try:
        subprocess.run(
            ["netsh", "advfirewall", "firewall", "set", "profile", "state", "off"],
            capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW
        )
        return True
    except Exception:
        return False
