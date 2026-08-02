from PySide6.QtCore import QThread, Signal

from vpn_configurator.core.config_parser import parse_subscription_all


class SubFetchThread(QThread):
    nodes_ready = Signal(list)
    error = Signal(str)

    def __init__(self, url):
        super().__init__()
        self.url = url

    def run(self):
        try:
            nodes = parse_subscription_all(self.url)
            self.nodes_ready.emit(nodes)
        except Exception as e:
            self.error.emit(str(e))