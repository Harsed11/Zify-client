import json
import os

from vpn_configurator.core.xray_manager import XRayThread


def _node(**over):
    node = {
        "type": "vless", "host": "h.com", "port": 443, "uuid": "u",
        "network": "tcp", "security": "none",
    }
    node.update(over)
    return node


def _write(tmp_path, node, routing, tun_mode=False):
    cfg = str(tmp_path / "config.json")
    t = XRayThread(cfg, node, routing, tun_mode=tun_mode)
    t._write_config()
    with open(cfg, encoding="utf-8") as f:
        return json.load(f)


def test_routing_always_includes_private_direct(tmp_path):
    data = _write(tmp_path, _node(), {"mode": "all", "custom_domains": []})
    rules = data["routing"]["rules"]
    assert {"type": "field", "ip": ["geoip:private"], "outboundTag": "direct"} in rules


def test_routing_bypass_includes_ru_direct(tmp_path):
    data = _write(tmp_path, _node(), {"mode": "bypass", "custom_domains": []})
    domains = [r.get("domain") for r in data["routing"]["rules"]]
    assert ["geosite:category-ru"] in domains


def test_routing_all_has_no_ru_rule(tmp_path):
    data = _write(tmp_path, _node(), {"mode": "all", "custom_domains": []})
    domains = [r.get("domain") for r in data["routing"]["rules"]]
    assert ["geosite:category-ru"] not in domains


def test_routing_custom_domains_get_prefix(tmp_path):
    data = _write(
        tmp_path,
        _node(),
        {"mode": "all", "custom_domains": ["example.com", "regexp:^ads\\.", "*.wild.com"]},
    )
    domains = [r.get("domain") for r in data["routing"]["rules"]]
    assert ["domain:example.com"] in domains
    assert ["regexp:^ads\\."] in domains
    assert ["*.wild.com"] in domains


def test_routing_catchall_proxy_last(tmp_path):
    data = _write(tmp_path, _node(), {"mode": "all", "custom_domains": []})
    rules = data["routing"]["rules"]
    assert rules[-1] == {"type": "field", "network": "tcp,udp", "outboundTag": "proxy"}


def test_routing_count_by_mode(tmp_path):
    all_rules = _write(tmp_path, _node(), {"mode": "all", "custom_domains": []})["routing"]["rules"]
    bypass = _write(tmp_path, _node(), {"mode": "bypass", "custom_domains": []})["routing"]["rules"]
    lan = _write(tmp_path, _node(), {"mode": "lan", "custom_domains": []})["routing"]["rules"]
    # rules: api + ipv6(proxy) + private + catchall-proxy
    assert len(all_rules) == 4
    assert len(bypass) == 5  # adds geosite:category-ru
    assert len(lan) == 4


def test_api_inbound_and_routing(tmp_path):
    data = _write(tmp_path, _node(), {"mode": "all", "custom_domains": []})
    api_tags = [i["tag"] for i in data["inbounds"]]
    assert "api" in api_tags
    assert data["routing"]["rules"][0] == {
        "type": "field", "inboundTag": ["api"], "outboundTag": "api"
    }


def test_tun_inbound_only_with_flag(tmp_path):
    on = _write(tmp_path, _node(), {"mode": "all", "custom_domains": []}, tun_mode=True)
    off = _write(tmp_path, _node(), {"mode": "all", "custom_domains": []}, tun_mode=False)
    assert "tun-in" in [i["tag"] for i in on["inbounds"]]
    assert "tun-in" not in [i["tag"] for i in off["inbounds"]]


def test_reality_settings_injected(tmp_path):
    node = _node(security="reality", pbk="pub", sid="sid", spx="/", sni="h.com")
    data = _write(tmp_path, node, {"mode": "all", "custom_domains": []})
    stream = data["outbounds"][0]["streamSettings"]
    assert stream["security"] == "reality"
    rs = stream["realitySettings"]
    assert rs["publicKey"] == "pub"
    assert rs["shortId"] == "sid"
    assert rs["spiderX"] == "/"
    assert rs["serverName"] == "h.com"


def test_outbounds_proxy_and_direct(tmp_path):
    data = _write(tmp_path, _node(), {"mode": "all", "custom_domains": []})
    tags = [o.get("tag") for o in data["outbounds"]]
    assert tags == ["proxy", "direct", "block"]
