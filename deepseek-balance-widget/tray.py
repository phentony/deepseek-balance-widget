# tray.py
from PySide6.QtWidgets import QSystemTrayIcon, QMenu
from PySide6.QtGui import QIcon, QAction, QPixmap, QPainter, QColor


def _make_tray_icon():
    pixmap = QPixmap(32, 32)
    pixmap.fill(QColor(0, 0, 0, 0))
    painter = QPainter(pixmap)
    painter.setBrush(QColor(166, 227, 161))
    painter.setPen(QColor(0, 0, 0, 0))
    painter.drawEllipse(4, 4, 24, 24)
    painter.setBrush(QColor(30, 30, 46))
    painter.drawEllipse(10, 10, 12, 12)
    painter.end()
    return QIcon(pixmap)


class TrayManager:
    def __init__(self, widget, config, refresh_callback=None, on_settings_changed=None):
        self._widget = widget
        self._config = config
        self._refresh_callback = refresh_callback
        self._on_settings_changed = on_settings_changed

        self._tray = QSystemTrayIcon()
        self._tray.setIcon(_make_tray_icon())
        self._tray.setToolTip("DeepSeek Balance")

        menu = QMenu()
        show_action = QAction("Show/Hide")
        show_action.triggered.connect(self._toggle_widget)
        menu.addAction(show_action)

        refresh_action = QAction("Refresh Now")
        refresh_action.triggered.connect(self._refresh)
        menu.addAction(refresh_action)

        menu.addSeparator()

        settings_action = QAction("Settings...")
        settings_action.triggered.connect(self._open_settings)
        menu.addAction(settings_action)

        menu.addSeparator()

        quit_action = QAction("Quit")
        quit_action.triggered.connect(self._quit)
        menu.addAction(quit_action)

        self._tray.setContextMenu(menu)
        self._tray.activated.connect(self._on_activated)
        self._tray.show()

    def _toggle_widget(self):
        self._widget.setVisible(not self._widget.isVisible())

    def _refresh(self):
        if self._refresh_callback:
            self._refresh_callback()

    def _open_settings(self):
        from settings_dialog import SettingsDialog
        dlg = SettingsDialog(
            api_key=self._config.get_api_key() or "",
            refresh_interval=self._config.get_refresh_interval(),
        )
        if dlg.exec():
            self._config.set_api_key(dlg.get_api_key())
            self._config.set_refresh_interval(dlg.get_refresh_interval())
            if self._on_settings_changed:
                self._on_settings_changed()
            if self._refresh_callback:
                self._refresh_callback()

    def _on_activated(self, reason):
        if reason == QSystemTrayIcon.Trigger:
            self._toggle_widget()

    def _quit(self):
        from PySide6.QtWidgets import QApplication
        QApplication.instance().quit()
