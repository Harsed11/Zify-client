import time
import urllib.request

from PySide6.QtCore import QThread, Signal

from vpn_configurator.core.xray_stats_pb2 import GetStatsRequest
from vpn_configurator.core.xray_stats_pb2_grpc import StatsServiceStub

import grpc

API_ADDR = "127.0.0.1:15490"
STATS_UPLINK = "outbound>>>proxy>>>traffic>>>uplink"
STATS_DOWNLINK = "outbound>>>proxy>>>traffic>>>downlink"


class TrafficStats(QThread):
    update_traffic = Signal(float, float)

    def __init__(self):
        super().__init__()
        self.running = True
        self._channel = None
        self._stub = None

    def run(self):
        try:
            self._connect()
        except Exception:
            self._stub = None

        last = time.time()
        while self.running:
            try:
                if self._stub is None:
                    self._connect()
                down = self._fetch(STATS_DOWNLINK)
                up = self._fetch(STATS_UPLINK)
            except Exception:
                self._stub = None
                down, up = 0.0, 0.0
            self.update_traffic.emit(float(down), float(up))
            time.sleep(1.0)

    def _connect(self):
        self._channel = grpc.insecure_channel(API_ADDR)
        for _ in range(20):
            try:
                grpc.channel_ready_future(self._channel).result(timeout=0.5)
                break
            except Exception:
                if not self.running:
                    raise
        self._stub = StatsServiceStub(self._channel)

    def _fetch(self, name):
        if self._stub is None:
            return 0.0
        try:
            resp = self._stub.GetStats(GetStatsRequest(name=name, reset=True), timeout=2)
            return resp.stat.value if resp.stat and resp.stat.name else 0.0
        except Exception:
            return 0.0

    def stop(self):
        self.running = False
        self.wait(3000)
        if self._channel is not None:
            try:
                self._channel.close()
            except Exception:
                pass
            self._channel = None


SPEED_TEST_URLS = [
    "https://speed.cloudflare.com/__down?bytes=5000000",
    "https://proof.ovh.net/files/5Mb.dat",
    "https://cdn.jsdelivr.net/gh/ciwch/testfiles/speedtest/5MB.zip",
]


class SpeedTestThread(QThread):
    progress = Signal(int)  # 0-100
    result = Signal(float, float)  # mbps, latency_ms
    error = Signal(str)

    def __init__(self, proxy=("127.0.0.1", 10809)):
        super().__init__()
        self.proxy = proxy

    def run(self):
        proxy_url = f"http://{self.proxy[0]}:{self.proxy[1]}"
        proxy_handler = urllib.request.ProxyHandler({
            "http": proxy_url,
            "https": proxy_url,
        })
        opener = urllib.request.build_opener(proxy_handler)

        # Measure latency first
        latencies = []
        for _ in range(3):
            try:
                start = time.time()
                opener.open("https://www.google.com/generate_204", timeout=5)
                latencies.append((time.time() - start) * 1000)
            except Exception:
                pass
        avg_latency = sum(latencies) / len(latencies) if latencies else -1.0

        # Download test
        total_bytes = 0
        start_time = time.time()
        timeout = 10

        for url in SPEED_TEST_URLS:
            try:
                resp = opener.open(url, timeout=timeout)
                chunk_size = 65536
                while True:
                    chunk = resp.read(chunk_size)
                    if not chunk:
                        break
                    total_bytes += len(chunk)
                    elapsed = time.time() - start_time
                    if elapsed >= timeout:
                        break
                    pct = min(99, int(total_bytes / (5 * 1024 * 1024) * 100))
                    self.progress.emit(pct)
            except Exception:
                continue
            if time.time() - start_time >= timeout:
                break

        elapsed = time.time() - start_time
        if elapsed > 0 and total_bytes > 0:
            mbps = (total_bytes * 8) / (elapsed * 1_000_000)
        else:
            mbps = 0.0
        self.progress.emit(100)
        self.result.emit(mbps, avg_latency)
