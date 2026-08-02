"""Split Tunneling — выбор приложений для маршрутизации через VPN."""
import os
import sys
import subprocess
import json
from pathlib import Path


SPLIT_TUNNEL_FILE = "split_apps.json"


def get_split_apps_path():
    """Путь к файлу со списком приложений."""
    base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    data_dir = os.path.join(base, "data")
    os.makedirs(data_dir, exist_ok=True)
    return os.path.join(data_dir, SPLIT_TUNNEL_FILE)


def load_split_apps():
    """Загрузить список приложений для split tunneling."""
    path = get_split_apps_path()
    if not os.path.isfile(path):
        return {"mode": "exclude", "apps": []}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"mode": "exclude", "apps": []}


def save_split_apps(data):
    """Сохранить список приложений."""
    path = get_split_apps_path()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def get_running_processes():
    """Получить список запущенных процессов (имя, путь)."""
    if sys.platform != "win32":
        return []
    try:
        result = subprocess.run(
            ["powershell", "-Command",
             "Get-Process | Where-Object {$_.Path} | Select-Object ProcessName, Path | ConvertTo-Json -Compress"],
            capture_output=True, text=True, timeout=10,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        if result.returncode != 0:
            return []
        data = json.loads(result.stdout)
        if isinstance(data, dict):
            data = [data]
        processes = []
        seen = set()
        for item in data:
            path = item.get("Path", "")
            if path and path not in seen:
                seen.add(path)
                processes.append({
                    "name": item.get("ProcessName", ""),
                    "path": path
                })
        return sorted(processes, key=lambda x: x["name"].lower())
    except Exception:
        return []


def add_app_to_split(path_str, mode="exclude"):
    """Добавить приложение в список."""
    data = load_split_apps()
    data["mode"] = mode
    if path_str not in data["apps"]:
        data["apps"].append(path_str)
    save_split_apps(data)


def remove_app_from_split(path_str):
    """Удалить приложение из списка."""
    data = load_split_apps()
    if path_str in data["apps"]:
        data["apps"].remove(path_str)
    save_split_apps(data)


def is_app_in_split(path_str):
    """Проверить, есть ли приложение в списке."""
    data = load_split_apps()
    return path_str in data.get("apps", [])


def generate_process_rules(apps, mode, proxy_port=10808):
    """Сгенерировать routing rules для xray на основе split tunneling.
    
    mode: "exclude" — все через VPN, кроме выбранных
          "include" — только выбранные через VPN
    """
    if not apps:
        return []
    
    rules = []
    
    if mode == "exclude":
        # Приложения в списке идут напрямую (мимо VPN)
        for app_path in apps:
            exe_name = os.path.basename(app_path)
            rules.append({
                "type": "field",
                "process": [exe_name],
                "outboundTag": "direct"
            })
    else:  # include
        # Только эти приложения через VPN
        process_names = [os.path.basename(p) for p in apps]
        if process_names:
            rules.append({
                "type": "field",
                "process": process_names,
                "outboundTag": "proxy"
            })
            # Всё остальное — напрямую
            rules.append({
                "type": "field",
                "network": "tcp,udp",
                "outboundTag": "direct"
            })
    
    return rules
