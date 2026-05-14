# main.py
import sys
import os

# Hide console on Windows when running as exe
if sys.platform == "win32" and getattr(sys, 'frozen', False):
    import ctypes
    ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer

from config import Config
from balance_api import fetch_balance, BalanceError
from widget import BalanceWidget
from tray import TrayManager


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    config = Config()
    widget = BalanceWidget(config)

    # If no API key, show settings on first run
    if not config.get_api_key():
        from settings_dialog import SettingsDialog
        dlg = SettingsDialog()
        if dlg.exec():
            config.set_api_key(dlg.get_api_key())
            config.set_refresh_interval(dlg.get_refresh_interval())
        else:
            sys.exit(0)

    def refresh():
        api_key = config.get_api_key()
        if not api_key:
            widget.show_error("No API key configured")
            return
        try:
            info = fetch_balance(api_key)
            widget.update_balance(info)
        except BalanceError as e:
            widget.show_error(str(e))

    # Initial fetch
    refresh()

    # Auto-refresh timer
    timer = QTimer()
    timer.timeout.connect(refresh)
    timer.start(config.get_refresh_interval() * 1000)

    def on_settings_changed():
        timer.setInterval(config.get_refresh_interval() * 1000)

    # System tray
    tray_ = TrayManager(widget, config, refresh_callback=refresh, on_settings_changed=on_settings_changed)

    widget.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
