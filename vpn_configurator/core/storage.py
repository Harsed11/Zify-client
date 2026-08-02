import os
import json

from vpn_configurator.core.paths import data_dir

STORAGE_PATH = os.path.join(data_dir(), "storage.json")


def _serializable(obj):
    if isinstance(obj, dict):
        return {k: _serializable(v) for k, v in obj.items() if isinstance(k, str)}
    if isinstance(obj, (list, tuple)):
        return [_serializable(v) for v in obj]
    if isinstance(obj, (str, int, float, bool)) or obj is None:
        return obj
    return None


def load_data():
    try:
        with open(STORAGE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"providers": [], "selected_provider": -1, "selected_node": -1, "settings": {}}


def save_data(providers, selected_provider, selected_node=-1, settings=None):
    os.makedirs(os.path.dirname(STORAGE_PATH), exist_ok=True)
    data = {
        "providers": [
            {
                "url": p["url"],
                "host": p["host"],
                "type": p.get("type", ""),
                "nodes": _serializable(p.get("nodes", [])),
            }
            for p in providers
        ],
        "selected_provider": selected_provider,
        "selected_node": selected_node,
        "settings": _serializable(settings) or {},
    }
    with open(STORAGE_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def export_backup(path, providers, selected_provider, selected_node=-1, settings=None):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    data = {
        "app": "zify-vpn",
        "version": 1,
        "providers": [
            {
                "url": p["url"],
                "host": p["host"],
                "type": p.get("type", ""),
                "nodes": _serializable(p.get("nodes", [])),
            }
            for p in providers
        ],
        "selected_provider": selected_provider,
        "selected_node": selected_node,
        "settings": _serializable(settings) or {},
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def import_backup(path):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return (
        data.get("providers", []),
        data.get("selected_provider", -1),
        data.get("selected_node", -1),
        data.get("settings", {}),
    )
