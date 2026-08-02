import json

import vpn_configurator.core.storage as storage


def _providers():
    return [
        {
            "url": "https://sub.example.com/x",
            "host": "p1",
            "type": "SUB",
            "nodes": [
                {
                    "type": "vless", "host": "h.com", "port": 443, "uuid": "u",
                    "network": "tcp", "security": "reality",
                    "pbk": "k", "ps": "🇩🇪 DE", "_favorite": True,
                }
            ],
        }
    ]


def test_save_load_roundtrip(monkeypatch, tmp_path):
    p = tmp_path / "storage.json"
    monkeypatch.setattr(storage, "STORAGE_PATH", str(p))
    storage.save_data(_providers(), 0, 0, {"auto_connect": True})
    data = storage.load_data()
    assert data["selected_provider"] == 0
    assert data["selected_node"] == 0
    assert data["settings"] == {"auto_connect": True}
    assert data["providers"][0]["host"] == "p1"
    assert data["providers"][0]["nodes"][0]["_favorite"] is True


def test_load_missing_file(monkeypatch, tmp_path):
    monkeypatch.setattr(storage, "STORAGE_PATH", str(tmp_path / "nope.json"))
    data = storage.load_data()
    assert data == {
        "providers": [], "selected_provider": -1, "selected_node": -1, "settings": {}
    }


def test_load_corrupted_file(monkeypatch, tmp_path):
    p = tmp_path / "storage.json"
    p.write_text("{not json", encoding="utf-8")
    monkeypatch.setattr(storage, "STORAGE_PATH", str(p))
    data = storage.load_data()
    assert data["providers"] == []


def test_serializable_strips_objects():
    import datetime
    assert storage._serializable(datetime.datetime.now()) is None
    assert storage._serializable({"a": 1, "b": object()}) == {"a": 1, "b": None}
    assert storage._serializable({"a": [1, None, True]}) == {"a": [1, None, True]}


def test_export_import_backup(monkeypatch, tmp_path):
    backup = tmp_path / "backup.json"
    storage.export_backup(str(backup), _providers(), 0, 0, {"kill_switch": True})
    assert backup.exists()
    data = json.loads(backup.read_text(encoding="utf-8"))
    assert data["app"] == "zify-vpn"
    providers, sp, sn, settings = storage.import_backup(str(backup))
    assert len(providers) == 1
    assert sp == 0 and sn == 0
    assert settings == {"kill_switch": True}
