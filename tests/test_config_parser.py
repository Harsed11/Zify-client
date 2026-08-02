import json
import base64

import pytest

from vpn_configurator.core.config_parser import (
    parse_config,
    parse_vless,
    parse_vmess,
    parse_trojan,
    parse_shadowsocks,
    parse_subscription_all,
)

def b64url(s):
    return base64.urlsafe_b64encode(s.encode()).decode().rstrip("=")


def test_parse_vless_reality():
    url = (
        "vless://uuid123@cdn.example.com:443?encryption=none&security=reality"
        "&type=tcp&sni=cdn.example.com&fp=chrome&pbk=publickey&sid=shortid"
        "&spx=%2F#%F0%9F%87%A9%F0%9F%87%AA%20DE%2001"
    )
    node = parse_vless(url)
    assert node["type"] == "vless"
    assert node["uuid"] == "uuid123"
    assert node["host"] == "cdn.example.com"
    assert node["port"] == 443
    assert node["security"] == "reality"
    assert node["sni"] == "cdn.example.com"
    assert node["fp"] == "chrome"
    assert node["pbk"] == "publickey"
    assert node["sid"] == "shortid"
    assert node["spx"] == "/"
    assert node["ps"] == "🇩🇪 DE 01"


def test_parse_vless_defaults():
    node = parse_vless("vless://u@host.com:8443")
    assert node["host"] == "host.com"
    assert node["port"] == 8443
    assert node["security"] == "none"
    assert node["network"] == "tcp"


def test_parse_vmess_json():
    payload = {
        "v": "2", "ps": "UK 01", "add": "vm.example.com", "port": "443",
        "id": "abc", "aid": "0", "net": "ws", "type": "none", "host": "",
        "path": "/ws", "tls": "tls", "sni": "vm.example.com",
    }
    url = "vmess://" + b64url(json.dumps(payload))
    node = parse_vmess(url)
    assert node["type"] == "vmess"
    assert node["uuid"] == "abc"
    assert node["host"] == "vm.example.com"
    assert node["port"] == 443
    assert node["network"] == "ws"
    assert node["security"] == "tls"
    assert node["ps"] == "UK 01"


def test_parse_trojan_remark():
    node = parse_trojan("trojan://pw@jp.example.com:443#Tokyo JP")
    assert node["type"] == "trojan"
    assert node["host"] == "jp.example.com"
    assert node["security"] == "tls"
    assert node["ps"] == "Tokyo JP"


def test_parse_shadowsocks():
    node = parse_shadowsocks(
        "ss://" + b64url("aes-256-gcm:secret@sg.example.com:8388") + "#Singapore"
    )
    assert node["type"] == "ss"
    assert node["host"] == "sg.example.com"
    assert node["port"] == 8388
    assert node["ps"] == "Singapore"


def test_parse_config_unsupported():
    with pytest.raises(ValueError):
        parse_config("weird://x")


def test_parse_subscription_all_lines(monkeypatch):
    payload = "\n".join(
        [
            "vless://u@a.com:443#ALPHA",
            "trojan://pw@b.com:443#BETA",
        ]
    )
    from vpn_configurator.core import config_parser
    monkeypatch.setattr(config_parser, "fetch_subscription_text", lambda url: payload)
    nodes = parse_subscription_all("https://example.com/sub")
    assert len(nodes) == 2
    assert nodes[0]["host"] == "a.com"
    assert nodes[1]["host"] == "b.com"


def test_parse_subscription_all_with_invalid_lines(monkeypatch):
    payload = "\n".join(
        [
            "not-a-link",
            "vless://u@a.com:443#ONE",
        ]
    )
    from vpn_configurator.core import config_parser
    monkeypatch.setattr(config_parser, "fetch_subscription_text", lambda url: payload)
    nodes = parse_subscription_all("https://example.com/sub")
    assert len(nodes) == 1
    assert nodes[0]["host"] == "a.com"
