"""XRay Updater — автоматическое обновление xray-core."""
import os
import sys
import json
import urllib.request
import urllib.error
import tempfile
import zipfile
import shutil
from pathlib import Path


UPDATE_CONFIG_FILE = "update_config.json"


def get_update_config_path():
    """Путь к файлу конфигурации обновлений."""
    base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    data_dir = os.path.join(base, "data")
    os.makedirs(data_dir, exist_ok=True)
    return os.path.join(data_dir, UPDATE_CONFIG_FILE)


def load_update_config():
    """Загрузить конфигурацию обновлений."""
    path = get_update_config_path()
    if not os.path.isfile(path):
        return {
            "auto_update": False,
            "check_interval": 24,  # часов
            "last_check": 0,
            "version": ""
        }
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {
            "auto_update": False,
            "check_interval": 24,
            "last_check": 0,
            "version": ""
        }


def save_update_config(data):
    """Сохранить конфигурацию обновлений."""
    path = get_update_config_path()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def get_xray_bin_path():
    """Путь к папке с xray.exe."""
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, "bin")


def get_current_version():
    """Получить текущую версию xray."""
    xray_path = os.path.join(get_xray_bin_path(), "xray.exe")
    if not os.path.isfile(xray_path):
        return "unknown"
    try:
        result = subprocess.run(
            [xray_path, "version"],
            capture_output=True, text=True, timeout=5,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        # Формат: Xray version 1.8.0 (Xray v1.8.0)
        if result.returncode == 0:
            output = result.stdout
            import re
            match = re.search(r'(\d+\.\d+\.\d+)', output)
            if match:
                return match.group(1)
        return "unknown"
    except Exception:
        return "unknown"


def check_for_updates():
    """Проверить наличие обновлений xray-core."""
    import time
    import subprocess
    
    config = load_update_config()
    current_time = time.time()
    
    # Проверяем интервал
    if current_time - config.get("last_check", 0) < config.get("check_interval", 24) * 3600:
        return None
    
    # Получаем последнюю версию с GitHub
    try:
        url = "https://api.github.com/repos/XTLS/Xray-core/releases/latest"
        req = urllib.request.Request(url, headers={"User-Agent": "ZifyVPN"})
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())
        
        latest_version = data.get("tag_name", "").lstrip("v")
        if not latest_version:
            return None
        
        current_version = get_current_version()
        
        # Обновляем время последней проверки
        config["last_check"] = current_time
        config["version"] = latest_version
        save_update_config(config)
        
        if latest_version != current_version:
            return {
                "current": current_version,
                "latest": latest_version,
                "url": data.get("html_url", ""),
                "assets": data.get("assets", [])
            }
        return None
    except Exception as e:
        return {"error": str(e)}


def download_xray_update():
    """Скачать и установить обновление xray."""
    import time
    
    update_info = check_for_updates()
    if not update_info or "error" in update_info:
        return False, update_info.get("error", "No update available")
    
    # Находим Windows архив
    assets = update_info.get("assets", [])
    download_url = None
    for asset in assets:
        name = asset.get("name", "")
        if "windows" in name.lower() and name.endswith(".zip"):
            download_url = asset.get("browser_download_url", "")
            break
    
    if not download_url:
        return False, "No Windows update found"
    
    try:
        # Скачиваем
        with urllib.request.urlopen(download_url, timeout=60) as response:
            zip_data = response.read()
        
        # Распаковываем во временную папку
        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = os.path.join(tmpdir, "xray.zip")
            with open(zip_path, "wb") as f:
                f.write(zip_data)
            
            with zipfile.ZipFile(zip_path, "r") as zip_ref:
                zip_ref.extractall(tmpdir)
            
            # Ищем xray.exe
            xray_new = None
            for root, dirs, files in os.walk(tmpdir):
                if "xray.exe" in files:
                    xray_new = os.path.join(root, "xray.exe")
                    break
            
            if not xray_new:
                return False, "xray.exe not found in archive"
            
            # Резервируем старый xray.exe
            bin_path = get_xray_bin_path()
            xray_old = os.path.join(bin_path, "xray.exe")
            xray_backup = os.path.join(bin_path, "xray.exe.bak")
            
            if os.path.isfile(xray_old):
                shutil.copy2(xray_old, xray_backup)
            
            # Копируем новый xray.exe
            shutil.copy2(xray_new, xray_old)
            
            # Обновляем версию
            config = load_update_config()
            config["last_check"] = time.time()
            config["version"] = update_info["latest"]
            save_update_config(config)
            
            return True, f"Updated to v{update_info['latest']}"
    except Exception as e:
        return False, str(e)


def auto_update_enabled():
    """Проверить, включено ли автообновление."""
    config = load_update_config()
    return config.get("auto_update", False)
