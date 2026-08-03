"""DNS Overriding — выбор DNS сервера и блокировка рекламы."""
import os
import json


DNS_CONFIG_FILE = "dns_config.json"


def get_dns_config_path():
    """Путь к файлу конфигурации DNS."""
    base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    data_dir = os.path.join(base, "data")
    os.makedirs(data_dir, exist_ok=True)
    return os.path.join(data_dir, DNS_CONFIG_FILE)


def load_dns_config():
    """Загрузить конфигурацию DNS."""
    path = get_dns_config_path()
    if not os.path.isfile(path):
        return {
            "dns": "system",
            "custom_dns": "",
            "block_ads": False,
            "block_trackers": False,
            "block_malware": False
        }
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {
            "dns": "system",
            "custom_dns": "",
            "block_ads": False,
            "block_trackers": False,
            "block_malware": False
        }


def save_dns_config(data):
    """Сохранить конфигурацию DNS."""
    path = get_dns_config_path()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# Предустановленные DNS серверы
PRESET_DNS = {
    "system": {"name": "Системный DNS", "servers": []},
    "google": {"name": "Google DNS", "servers": ["8.8.8.8", "8.8.4.4"]},
    "cloudflare": {"name": "Cloudflare DNS", "servers": ["1.1.1.1", "1.0.0.1"]},
    "quad9": {"name": "Quad9 (безопасный)", "servers": ["9.9.9.9", "149.112.112.112"]},
    "opendns": {"name": "OpenDNS", "servers": ["208.67.222.222", "208.67.220.220"]},
    "adguard": {"name": "AdGuard (без рекламы)", "servers": ["94.140.14.14", "94.140.15.15"]},
    "custom": {"name": "Пользовательский", "servers": []}
}


def get_preset_dns_list():
    """Список предустановленных DNS серверов."""
    return [
        {"id": "system", "name": PRESET_DNS["system"]["name"]},
        {"id": "google", "name": PRESET_DNS["google"]["name"]},
        {"id": "cloudflare", "name": PRESET_DNS["cloudflare"]["name"]},
        {"id": "quad9", "name": PRESET_DNS["quad9"]["name"]},
        {"id": "opendns", "name": PRESET_DNS["opendns"]["name"]},
        {"id": "adguard", "name": PRESET_DNS["adguard"]["name"]},
        {"id": "custom", "name": PRESET_DNS["custom"]["name"]}
    ]


def generate_dns_config(dns_config):
    """Сгенерировать DNS конфигурацию для xray."""
    dns = dns_config.get("dns", "system")
    custom_dns = dns_config.get("custom_dns", "")
    block_ads = dns_config.get("block_ads", False)
    block_trackers = dns_config.get("block_trackers", False)
    block_malware = dns_config.get("block_malware", False)
    
    # Список DNS серверов
    servers = []
    
    if dns == "system":
        servers = ["localhost"]
    elif dns == "custom":
        # Пользовательский DNS
        if custom_dns:
            servers = [s.strip() for s in custom_dns.split(",") if s.strip()]
        if not servers:
            servers = ["8.8.8.8", "8.8.4.4"]
    elif dns in PRESET_DNS:
        servers = PRESET_DNS[dns]["servers"]
    else:
        servers = ["8.8.8.8", "8.8.4.4"]
    
    # Генерация конфигурации DNS
    dns_rules = []
    
    # Блокировка рекламы через hosts
    if block_ads or block_trackers or block_malware:
        # Используем built-in hosts plugin для блокировки
        hosts = []
        if block_ads:
            hosts.extend([
                "doubleclick.net", "googleadservices.com", "adservice.google.com",
                "pagead2.googlesyndication.com", "ads.yahoo.com", "ad.doubleclick.net"
            ])
        if block_trackers:
            hosts.extend([
                "analytics.google.com", "tracking.google.com", "stats.g.doubleclick.net"
            ])
        if block_malware:
            hosts.extend([
                "malware.domain.com", "phishing.domain.com"
            ])
        
        if hosts:
            dns_rules.append({
                "type": "field",
                "domain": [f"full:{h}" for h in hosts],
                "outboundTag": "block"
            })
    
    return {
        "servers": servers,
    }, dns_rules
