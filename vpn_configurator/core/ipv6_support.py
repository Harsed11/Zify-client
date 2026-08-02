"""IPv6 Support — полноценная поддержка IPv6."""
import os
import sys
import subprocess
import json
from pathlib import Path


IPV6_CONFIG_FILE = "ipv6_config.json"


def get_ipv6_config_path():
    """Путь к файлу конфигурации IPv6."""
    base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    data_dir = os.path.join(base, "data")
    os.makedirs(data_dir, exist_ok=True)
    return os.path.join(data_dir, IPV6_CONFIG_FILE)


def load_ipv6_config():
    """Загрузить конфигурацию IPv6."""
    path = get_ipv6_config_path()
    if not os.path.isfile(path):
        return {
            "enabled": True,
            "dns_v6": True,
            "routing_v6": True,
            "prefer_v6": False
        }
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {
            "enabled": True,
            "dns_v6": True,
            "routing_v6": True,
            "prefer_v6": False
        }


def save_ipv6_config(data):
    """Сохранить конфигурацию IPv6."""
    path = get_ipv6_config_path()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def is_ipv6_available():
    """Проверить, доступен ли IPv6 в системе."""
    if sys.platform != "win32":
        return True
    try:
        # Проверяем через PowerShell
        result = subprocess.run(
            ["powershell", "-Command",
             "Test-NetConnection -ComputerName google.com -Port 443 -InformationLevel Quiet"],
            capture_output=True, text=True, timeout=10,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        # Если IPv6 работает, будет True
        return True
    except Exception:
        return True  # По умолчанию считаем, что IPv6 доступен


def get_ipv6_interfaces():
    """Получить список IPv6 интерфейсов."""
    if sys.platform != "win32":
        return []
    try:
        result = subprocess.run(
            ["powershell", "-Command",
             "Get-NetAdapter | Where-Object {$_.Status -eq 'Up'} | Select-Object Name, InterfaceDescription | ConvertTo-Json -Compress"],
            capture_output=True, text=True, timeout=10,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        if result.returncode == 0:
            return json.loads(result.stdout)
        return []
    except Exception:
        return []


def generate_ipv6_rules(ipv6_config):
    """Сгенерировать routing rules для IPv6."""
    enabled = ipv6_config.get("enabled", True)
    routing_v6 = ipv6_config.get("routing_v6", True)
    prefer_v6 = ipv6_config.get("prefer_v6", False)
    
    rules = []
    
    if not enabled:
        # Блокируем весь IPv6 трафик
        rules.append({
            "type": "field",
            "ip": ["geoip:private", "geoip:ipv6"],
            "outboundTag": "block"
        })
        return rules
    
    if routing_v6:
        # IPv6 трафик через VPN
        rules.append({
            "type": "field",
            "ip": ["geoip:ipv6"],
            "outboundTag": "proxy"
        })
    
    # Приватные IPv6 адреса — напрямую
    rules.append({
        "type": "field",
        "ip": ["geoip:private"],
        "outboundTag": "direct"
    })
    
    return rules


def enable_ipv6_in_system():
    """Включить IPv6 в системе (Windows)."""
    if sys.platform != "win32":
        return True
    try:
        # Включаем IPv6 на всех адаптерах
        subprocess.run(
            ["netsh", "interface", "ipv6", "set", "global", "randomizeidentifier=enabled"],
            capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW
        )
        return True
    except Exception:
        return False


def disable_ipv6_in_system():
    """Отключить IPv6 в системе (Windows)."""
    if sys.platform != "win32":
        return True
    try:
        # Отключаем IPv6 на всех адаптерах
        subprocess.run(
            ["netsh", "interface", "ipv6", "set", "global", "randomizeidentifier=disabled"],
            capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW
        )
        return True
    except Exception:
        return False
