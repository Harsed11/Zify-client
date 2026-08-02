import json
import socket
import ssl
import urllib.request
from urllib.parse import urlparse

from PySide6.QtCore import QThread, Signal

DEFAULT_PROXY = ("127.0.0.1", 10809)
CHECK_URL = "https://api.ipify.org/?format=json"
TIMEOUT = 8


class HealthCheckThread(QThread):
    done = Signal(str, bool)  # (ip_or_error, ok)

    def __init__(self, proxy=DEFAULT_PROXY, url=CHECK_URL):
        super().__init__()
        self.proxy = proxy
        self.url = url

    def run(self):
        proxy_handler = urllib.request.ProxyHandler({
            "http": f"http://{self.proxy[0]}:{self.proxy[1]}",
            "https": f"http://{self.proxy[0]}:{self.proxy[1]}",
        })
        opener = urllib.request.build_opener(proxy_handler)
        try:
            resp = opener.open(self.url, timeout=TIMEOUT)
            body = resp.read().decode("utf-8", "replace")
            ip = body.strip()
            try:
                data = json.loads(body)
                ip = data.get("ip", body.strip())
            except Exception:
                pass
            if ip:
                self.done.emit(ip, True)
            else:
                self.done.emit("No IP returned", False)
        except Exception as e:
            self.done.emit(str(e), False)
