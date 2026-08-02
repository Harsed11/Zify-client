import pytest
from PySide6.QtWidgets import QApplication

from vpn_configurator.ui.main_window import MainWindow


def _node(host, proto="vless", fav=False, latency=None, ps=""):
    n = {
        "type": proto, "host": host, "port": 443, "uuid": "u",
        "network": "tcp", "security": "none", "ps": ps,
    }
    if fav:
        n["_favorite"] = True
    if latency is not None:
        n["_latency"] = latency
    return n


@pytest.fixture()
def window(qapp):
    w = MainWindow()
    w.providers = [
        {"host": "p1", "type": "SUB", "url": "x", "nodes": [
            _node("de1.example.com", fav=True, latency=10, ps="🇩🇪 DE 01"),
            _node("de2.example.com", latency=5, ps="DE 02"),
            _node("jp.example.com", latency=50, ps="🇯🇵 JP 01"),
            _node("us.example.com", latency=30, ps="US 01"),
        ]},
    ]
    w.selected_provider_index = 0
    w.selected_node_index = 0
    w._refresh_country_filter()
    return w


def test_visible_all(window):
    idx = window._visible_node_indices(window.providers[0]["nodes"])
    assert idx == [0, 1, 2, 3]


def test_filter_proto(window):
    window._filter_proto = "vless"
    assert window._visible_node_indices(window.providers[0]["nodes"]) == [0, 1, 2, 3]
    window._filter_proto = "ss"
    assert window._visible_node_indices(window.providers[0]["nodes"]) == []


def test_filter_country(window):
    window._filter_country = "Германия"
    idx = window._visible_node_indices(window.providers[0]["nodes"])
    assert idx == [0, 1]
    window._filter_country = "Япония"
    idx = window._visible_node_indices(window.providers[0]["nodes"])
    assert idx == [2]


def test_filter_query(window):
    window._filter_query = "de1"
    idx = window._visible_node_indices(window.providers[0]["nodes"])
    assert idx == [0]
    window._filter_query = "jp"
    idx = window._visible_node_indices(window.providers[0]["nodes"])
    assert idx == [2]
    window._filter_query = "nothing-here"
    assert window._visible_node_indices(window.providers[0]["nodes"]) == []


def test_filter_favorites(window):
    window._fav_only = True
    idx = window._visible_node_indices(window.providers[0]["nodes"])
    assert idx == [0]


def test_top3_sorts_by_latency(window):
    window._top3 = True
    idx = window._visible_node_indices(window.providers[0]["nodes"])
    assert idx == [1, 0, 3]


def test_country_combo_entries(window):
    labels = [window.country_combo.itemText(i) for i in range(window.country_combo.count())]
    assert labels[0] == "All countries"
    assert "🇩🇪" in " ".join(labels)
    assert "🇯🇵" in " ".join(labels)


def test_toggle_favorite_persists(window):
    assert window.providers[0]["nodes"][1].get("_favorite") is None
    window._toggle_favorite(0, 1)
    assert window.providers[0]["nodes"][1].get("_favorite") is True
    window._toggle_favorite(0, 1)
    assert window.providers[0]["nodes"][1].get("_favorite") is False


def test_toggle_favorite_out_of_range(window):
    window._toggle_favorite(0, 99)
    window._toggle_favorite(9, 0)
