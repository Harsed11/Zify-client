import sys
import os

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from PySide6.QtWidgets import QApplication, QMessageBox
from vpn_configurator.core.singleton import acquire_single_instance
from vpn_configurator.ui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    if not acquire_single_instance():
        QMessageBox.information(
            None, "Zify client",
            "Zify client is already running.\nThe existing window was brought to the foreground."
        )
        return
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
