import os
import json
import subprocess
import sys
import tempfile
from PySide6.QtCore import QThread, Signal

from vpn_configurator.core.split_tunnel import load_split_apps, generate_process_rules
from vpn_configurator.core.dns_override import load_dns_config, generate_dns_config
from vpn_configurator.core.ipv6_support import load_ipv6_config, generate_ipv6_rules


class XRayThread(QThread):
    success = Signal(str)
    error = Signal(str)
    log_line = Signal(str)

    def __init__(self, config_file, node_data=None, routing=None, tun_mode=False):
        super().__init__()
        self.config_file = config_file
        self.node_data = node_data or {}
        self.routing = routing or {}
        self.tun_mode = tun_mode
        self.process = None
        self._stop_flag = False
        self._dns_config = load_dns_config()
        self._ipv6_config = load_ipv6_config()
        self._split_config = load_split_apps()

    def run(self):
        xray_path = self._find_xray()
        if not xray_path:
            self.error.emit("xray.exe not found in bin/ directory")
            return

        if not self.config_file:
            self.error.emit("No config file specified")
            return

        self._write_config()

        try:
            kwargs = {}
            if sys.platform == "win32":
                kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW

            self.process = subprocess.Popen(
                [xray_path, "run", "-config", self.config_file],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                cwd=os.path.dirname(xray_path),
                **kwargs,
            )

            self.success.emit("Xray process started successfully")
        except Exception as e:
            self.error.emit(str(e))
            return

        while not self._stop_flag:
            if not self.process or not self.process.stdout:
                break
            line = self.process.stdout.readline()
            if not line:
                break
            text = line.decode("utf-8", errors="replace").rstrip()
            if text:
                self.log_line.emit(text)

        if not self._stop_flag:
            rc = self.process.returncode if self.process else "?"
            self.error.emit(f"Xray process exited unexpectedly (code {rc})")

    def _find_xray(self):
        candidates = []
        if getattr(sys, "frozen", False):
            candidates.append(os.path.join(sys._MEIPASS, "bin", "xray.exe"))
            candidates.append(os.path.join(os.path.dirname(sys.executable), "bin", "xray.exe"))
        base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        bin_dir = os.path.join(base, "vpn_configurator", "bin")
        for name in ("xray.exe", "xray"):
            candidates.append(os.path.join(bin_dir, name))
        for path in candidates:
            if path and os.path.isfile(path):
                return path
        return None

    def _write_config(self):
        if not self.config_file:
            return

        n = self.node_data
        proto = n.get("type", "vmess")
        host = n.get("host", "127.0.0.1")
        port = int(n.get("port", 443))
        uuid = n.get("uuid", "")
        network = n.get("network", "tcp")
        security = n.get("security", "none")
        path = n.get("path", "")
        sni = n.get("sni", "")
        encryption = n.get("encryption", "auto")
        alpn = n.get("alpn", "")

        outbound = {
            "tag": "proxy",
            "protocol": proto,
            "settings": {},
            "streamSettings": {
                "network": network,
                "security": security,
            },
        }

        if security == "tls":
            tls_settings = {"serverName": sni or host, "allowInsecure": False}
            if alpn:
                tls_settings["alpn"] = [alpn] if isinstance(alpn, str) else alpn
            outbound["streamSettings"]["tlsSettings"] = tls_settings
        elif security == "reality":
            reality_settings = {
                "serverName": sni or host,
                "show": False,
                "fingerprint": n.get("fp") or "chrome",
                "publicKey": n.get("pbk") or "",
                "shortId": n.get("sid") or "",
            }
            if n.get("spx"):
                reality_settings["spiderX"] = n.get("spx")
            outbound["streamSettings"]["realitySettings"] = reality_settings

        if network == "ws":
            ws_settings = {}
            if path:
                ws_settings["path"] = path
            if sni:
                ws_settings["headers"] = {"Host": sni}
            outbound["streamSettings"]["wsSettings"] = ws_settings
        elif network == "grpc":
            grpc_settings = {}
            if path:
                grpc_settings["serviceName"] = path
            authority = n.get("authority", "")
            if authority:
                grpc_settings["authority"] = authority
            outbound["streamSettings"]["grpcSettings"] = grpc_settings
        elif network in ("h2", "http"):
            h2_settings = {}
            if path:
                h2_settings["path"] = path
            if sni:
                h2_settings["host"] = [sni]
            outbound["streamSettings"]["httpSettings"] = h2_settings

        if proto == "vmess":
            outbound["settings"] = {
                "vnext": [
                    {
                        "address": host,
                        "port": port,
                        "users": [
                            {
                                "id": uuid,
                                "security": encryption,
                                "level": 0,
                            }
                        ],
                    }
                ]
            }
        elif proto == "vless":
            user = {"id": uuid, "encryption": encryption, "level": 0}
            flow = n.get("flow", "")
            if flow:
                user["flow"] = flow
            outbound["settings"] = {
                "vnext": [
                    {
                        "address": host,
                        "port": port,
                        "users": [user],
                    }
                ]
            }
        elif proto == "trojan":
            outbound["settings"] = {
                "servers": [
                    {
                        "address": host,
                        "port": port,
                        "password": uuid,
                        "level": 0,
                    }
                ]
            }
        elif proto == "ss":
            method, sep, pwd = uuid.partition(":")
            outbound["settings"] = {
                "servers": [
                    {
                        "address": host,
                        "port": port,
                        "method": method or n.get("encryption", "aes-256-gcm"),
                        "password": pwd or uuid,
                        "level": 0,
                    }
                ]
            }
        else:
            self.error.emit(f"Unsupported protocol: {proto}")
            return

        socks_port = 10808
        http_port = 10809
        api_port = 15490

        config_data = {
            "log": {"loglevel": "warning"},
            "api": {
                "tag": "api",
                "services": ["HandlerService", "LoggerService", "StatsService", "ReflectionService"],
            },
            "policy": {
                "levels": {"0": {"statsUserUplink": True, "statsUserDownlink": True}}
            },
            "inbounds": [
                {
                    "tag": "socks-in",
                    "port": socks_port,
                    "listen": "127.0.0.1",
                    "protocol": "socks",
                    "settings": {
                        "udp": True,
                        "auth": "noauth",
                    },
                    "sniffing": {
                        "enabled": True,
                        "destOverride": ["http", "tls"],
                    },
                },
                {
                    "tag": "http-in",
                    "port": http_port,
                    "listen": "127.0.0.1",
                    "protocol": "http",
                    "settings": {},
                },
                {
                    "tag": "api",
                    "listen": "127.0.0.1",
                    "port": api_port,
                    "protocol": "dokodemo-door",
                    "settings": {"address": "127.0.0.1", "port": api_port},
                },
            ] + self._tun_inbounds(),
            "outbounds": [
                outbound,
                {"tag": "direct", "protocol": "freedom"},
                {"tag": "block", "protocol": "blackhole"},
            ],
        }

        dns_config, dns_rules = generate_dns_config(self._dns_config)
        config_data["dns"] = dns_config

        rules = [{"type": "field", "inboundTag": ["api"], "outboundTag": "api"}]
        rules.extend(dns_rules)

        if self.tun_mode:
            rules.append(
                {"type": "field", "inboundTag": ["tun-in"], "network": "tcp,udp", "outboundTag": "proxy"}
            )

        split_rules = generate_process_rules(
            self._split_config.get("apps", []),
            self._split_config.get("mode", "exclude")
        )
        rules.extend(split_rules)

        ipv6_rules = generate_ipv6_rules(self._ipv6_config)
        rules.extend(ipv6_rules)

        rules.extend(self._build_routing_rules())
        config_data["routing"] = {
            "domainStrategy": "AsIs",
            "rules": rules,
        }

        with open(self.config_file, "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=4)

    def _tun_inbounds(self):
        if not self.tun_mode:
            return []
        return [
            {
                "tag": "tun-in",
                "protocol": "tun",
                "settings": {
                    "interface_name": "zify0",
                    "mtu": 1500,
                    "networks": ["tcp", "udp"],
                },
                "sniffing": {"enabled": True, "destOverride": ["http", "tls", "quic"]},
            }
        ]

    def _build_routing_rules(self):
        mode = self.routing.get("mode", "all")
        custom = [d.strip() for d in (self.routing.get("custom_domains") or []) if d.strip()]

        rules = [
            {"type": "field", "ip": ["geoip:private"], "outboundTag": "direct"},
        ]

        if mode == "bypass":
            rules.append(
                {"type": "field", "domain": ["geosite:category-ru"], "outboundTag": "direct"}
            )

        prefixes = ("domain:", "regexp:", "geosite:", "geoip:", "full:", "keyword:")
        for domain in custom:
            entry = domain
            if not domain.startswith(prefixes) and "*" not in domain and not domain.startswith("."):
                entry = f"domain:{domain}"
            rules.append({"type": "field", "domain": [entry], "outboundTag": "direct"})

        rules.append({"type": "field", "network": "tcp,udp", "outboundTag": "proxy"})
        return rules

    def stop(self):
        self._stop_flag = True
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=3)
            except Exception:
                try:
                    self.process.kill()
                except Exception:
                    pass
            self.process = None
