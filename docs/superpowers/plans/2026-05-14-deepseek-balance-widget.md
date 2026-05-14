# DeepSeek Balance Desktop Widget Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a floating desktop widget showing DeepSeek API account balance with auto-refresh and system tray integration.

**Architecture:** Single Python process — PySide6 frameless always-on-top panel + QTimer-driven HTTP polling of DeepSeek `/user/balance` endpoint. API key stored via keyring (or local config fallback). Packaged with PyInstaller.

**Tech Stack:** Python 3.11+, PySide6, requests, keyring, PyInstaller

---

### Task 1: Project Scaffold

**Files:**
- Create: `deepseek-balance-widget/requirements.txt`
- Create: `deepseek-balance-widget/config.py`
- Create: `deepseek-balance-widget/tests/test_config.py`

- [ ] **Step 1: Write requirements.txt**

```
PySide6>=6.6.0
requests>=2.31.0
keyring>=24.0.0
```

- [ ] **Step 2: Write failing tests for config**

```python
# tests/test_config.py
import os
import json
import tempfile
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import Config


def test_config_creates_defaults():
    tmp = tempfile.mkdtemp()
    cfg = Config(config_dir=tmp)
    assert cfg.get_refresh_interval() == 300
    assert cfg.get_api_key() is None


def test_config_save_and_load_api_key():
    tmp = tempfile.mkdtemp()
    cfg = Config(config_dir=tmp)
    cfg.set_api_key("sk-test-key-123")
    assert cfg.get_api_key() == "sk-test-key-123"

    cfg2 = Config(config_dir=tmp)
    assert cfg2.get_api_key() == "sk-test-key-123"


def test_config_refresh_interval():
    tmp = tempfile.mkdtemp()
    cfg = Config(config_dir=tmp)
    cfg.set_refresh_interval(600)
    assert cfg.get_refresh_interval() == 600
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `cd deepseek-balance-widget && python -m pytest tests/test_config.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'config'`

- [ ] **Step 4: Implement config.py**

```python
# config.py
import os
import json
from pathlib import Path


class Config:
    def __init__(self, config_dir=None):
        self._dir = Path(config_dir or os.path.join(os.path.expanduser("~"), ".deepseek-widget"))
        self._dir.mkdir(parents=True, exist_ok=True)
        self._file = self._dir / "config.json"
        self._data = {}
        self._load()

    def _load(self):
        if self._file.exists():
            self._data = json.loads(self._file.read_text(encoding="utf-8"))

    def _save(self):
        self._file.write_text(json.dumps(self._data, indent=2), encoding="utf-8")

    def get_api_key(self):
        return self._data.get("api_key")

    def set_api_key(self, key):
        self._data["api_key"] = key
        self._save()

    def get_refresh_interval(self):
        return self._data.get("refresh_interval", 300)

    def set_refresh_interval(self, seconds):
        self._data["refresh_interval"] = seconds
        self._save()
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd deepseek-balance-widget && python -m pytest tests/test_config.py -v`
Expected: PASS (3 tests)

- [ ] **Step 6: Commit**

```bash
git add requirements.txt config.py tests/test_config.py
git commit -m "feat: add config module with API key and settings persistence"
```

---

### Task 2: Balance API Client

**Files:**
- Create: `deepseek-balance-widget/balance_api.py`
- Create: `deepseek-balance-widget/tests/test_balance_api.py`

- [ ] **Step 1: Write failing tests for balance API**

```python
# tests/test_balance_api.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from balance_api import fetch_balance, BalanceError, BalanceInfo


def test_balance_info_from_response():
    resp = {
        "is_available": True,
        "balance_infos": [
            {
                "currency": "CNY",
                "total_balance": "110.50",
                "granted_balance": "10.50",
                "topped_up_balance": "100.00"
            }
        ]
    }
    info = BalanceInfo.from_response(resp)
    assert info.is_available is True
    assert info.currency == "CNY"
    assert info.total_balance == 110.50
    assert info.granted_balance == 10.50
    assert info.topped_up_balance == 100.00


def test_balance_info_str_representation():
    info = BalanceInfo(True, "CNY", 88.00, 8.00, 80.00)
    s = str(info)
    assert "88.00" in s
    assert "CNY" in s


def test_fetch_balance_http_error(monkeypatch):
    import balance_api as ba

    def mock_get(*args, **kwargs):
        raise ba.requests.ConnectionError("network down")
    monkeypatch.setattr(ba.requests, "get", mock_get)

    with pytest.raises(BalanceError, match="network"):
        fetch_balance("sk-test")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd deepseek-balance-widget && python -m pytest tests/test_balance_api.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement balance_api.py**

```python
# balance_api.py
import requests

BALANCE_URL = "https://api.deepseek.com/user/balance"
TIMEOUT = 10


class BalanceError(Exception):
    pass


class BalanceInfo:
    def __init__(self, is_available, currency, total_balance, granted_balance, topped_up_balance):
        self.is_available = is_available
        self.currency = currency
        self.total_balance = total_balance
        self.granted_balance = granted_balance
        self.topped_up_balance = topped_up_balance

    @classmethod
    def from_response(cls, data):
        bi = data["balance_infos"][0]
        return cls(
            is_available=data["is_available"],
            currency=bi["currency"],
            total_balance=float(bi["total_balance"]),
            granted_balance=float(bi["granted_balance"]),
            topped_up_balance=float(bi["topped_up_balance"]),
        )

    def __str__(self):
        return f"Balance({self.currency} {self.total_balance:.2f}, available={self.is_available})"


def fetch_balance(api_key):
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    try:
        resp = requests.get(BALANCE_URL, headers=headers, timeout=TIMEOUT)
    except requests.RequestException as e:
        raise BalanceError(f"network error: {e}") from e

    if resp.status_code == 401:
        raise BalanceError("invalid API key (401)")
    if resp.status_code != 200:
        raise BalanceError(f"API error: HTTP {resp.status_code}")

    return BalanceInfo.from_response(resp.json())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd deepseek-balance-widget && python -m pytest tests/test_balance_api.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add balance_api.py tests/test_balance_api.py
git commit -m "feat: add balance API client for DeepSeek /user/balance endpoint"
```

---

### Task 3: Settings Dialog

**Files:**
- Create: `deepseek-balance-widget/settings_dialog.py`

- [ ] **Step 1: Implement settings_dialog.py**

```python
# settings_dialog.py
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QSpinBox, QPushButton, QFormLayout,
)
from PySide6.QtCore import Qt


class SettingsDialog(QDialog):
    def __init__(self, api_key="", refresh_interval=300, parent=None):
        super().__init__(parent)
        self.setWindowTitle("DeepSeek Balance Widget — Settings")
        self.setFixedSize(420, 220)
        self.setWindowFlags(Qt.Dialog | Qt.WindowCloseButtonHint)

        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        form = QFormLayout()
        form.setSpacing(10)

        self.key_input = QLineEdit()
        self.key_input.setPlaceholderText("sk-xxxxxxxxxxxxxxxx")
        self.key_input.setEchoMode(QLineEdit.Password)
        self.key_input.setText(api_key)
        form.addRow("API Key:", self.key_input)

        self.interval_input = QSpinBox()
        self.interval_input.setRange(30, 3600)
        self.interval_input.setSuffix(" seconds")
        self.interval_input.setValue(refresh_interval)
        form.addRow("Refresh Interval:", self.interval_input)

        layout.addLayout(form)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        save_btn = QPushButton("Save")
        save_btn.setDefault(True)
        save_btn.clicked.connect(self.accept)
        btn_layout.addWidget(save_btn)

        layout.addLayout(btn_layout)

    def get_api_key(self):
        return self.key_input.text().strip()

    def get_refresh_interval(self):
        return self.interval_input.value()
```

- [ ] **Step 2: Commit**

```bash
git add settings_dialog.py
git commit -m "feat: add settings dialog for API key and refresh interval"
```

---

### Task 4: Balance Widget Panel

**Files:**
- Create: `deepseek-balance-widget/widget.py`

- [ ] **Step 1: Implement widget.py**

```python
# widget.py
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QGridLayout,
)
from PySide6.QtCore import Qt, QPoint, QTimer
from PySide6.QtGui import QFont, QMouseEvent, QColor, QPalette


class BalanceWidget(QWidget):
    def __init__(self, config):
        super().__init__()
        self._config = config
        self._drag_pos = None
        self._init_ui()

    def _init_ui(self):
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground, False)
        self.setFixedSize(300, 200)

        self.setAutoFillBackground(True)
        pal = self.palette()
        pal.setColor(QPalette.Window, QColor(30, 30, 46))
        self.setPalette(pal)

        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        # Header row
        header = QHBoxLayout()
        title = QLabel("DeepSeek")
        title.setStyleSheet("color: #cdd6f4; font-size: 13px; font-weight: 600;")
        header.addWidget(title)
        header.addStretch()
        self._status_label = QLabel("OK")
        self._status_label.setStyleSheet("color: #a6e3a1; font-size: 11px;")
        header.addWidget(self._status_label)
        layout.addLayout(header)

        # Balance display
        self._balance_label = QLabel("--.--")
        self._balance_label.setStyleSheet("color: #a6e3a1; font-size: 36px; font-weight: 700;")
        self._balance_label.setAlignment(Qt.AlignLeft)
        layout.addWidget(self._balance_label)

        self._currency_label = QLabel("CNY")
        self._currency_label.setStyleSheet("color: #6c7086; font-size: 13px;")
        layout.addWidget(self._currency_label)

        # Detail grid
        grid = QGridLayout()
        grid.setSpacing(8)

        granted_title = QLabel("Granted")
        granted_title.setStyleSheet("color: #6c7086; font-size: 11px;")
        grid.addWidget(granted_title, 0, 0)

        self._granted_label = QLabel("--")
        self._granted_label.setStyleSheet("color: #89b4fa; font-size: 16px; font-weight: 600;")
        grid.addWidget(self._granted_label, 1, 0)

        topped_title = QLabel("Topped Up")
        topped_title.setStyleSheet("color: #6c7086; font-size: 11px;")
        grid.addWidget(topped_title, 0, 1)

        self._topped_label = QLabel("--")
        self._topped_label.setStyleSheet("color: #89b4fa; font-size: 16px; font-weight: 600;")
        grid.addWidget(self._topped_label, 1, 1)

        layout.addLayout(grid)

        # Footer
        footer = QHBoxLayout()
        self._updated_label = QLabel("Not updated yet")
        self._updated_label.setStyleSheet("color: #45475a; font-size: 10px;")
        footer.addWidget(self._updated_label)
        layout.addLayout(footer)

    def update_balance(self, balance_info):
        self._balance_label.setText(f"{balance_info.total_balance:.2f}")
        self._currency_label.setText(balance_info.currency)
        self._granted_label.setText(f"{balance_info.granted_balance:.2f}")
        self._topped_label.setText(f"{balance_info.topped_up_balance:.2f}")

        color = "#a6e3a1" if balance_info.total_balance > 1.0 else "#f38ba8"
        self._balance_label.setStyleSheet(
            f"color: {color}; font-size: 36px; font-weight: 700;"
        )

        self._status_label.setText("OK")
        self._status_label.setStyleSheet("color: #a6e3a1; font-size: 11px;")

        from datetime import datetime
        self._updated_label.setText(f"Updated {datetime.now().strftime('%H:%M:%S')}")

    def show_error(self, message):
        self._status_label.setText("ERROR")
        self._status_label.setStyleSheet("color: #f38ba8; font-size: 11px;")
        self._updated_label.setText(message)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event: QMouseEvent):
        if event.buttons() & Qt.LeftButton and self._drag_pos is not None:
            self.move(event.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, event: QMouseEvent):
        self._drag_pos = None
```

- [ ] **Step 2: Commit**

```bash
git add widget.py
git commit -m "feat: add floating balance widget panel with drag support"
```

---

### Task 5: System Tray

**Files:**
- Create: `deepseek-balance-widget/tray.py`

- [ ] **Step 1: Implement tray.py**

```python
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
    def __init__(self, widget, config, refresh_callback=None):
        self._widget = widget
        self._config = config
        self._refresh_callback = refresh_callback

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
            if self._refresh_callback:
                self._refresh_callback()

    def _on_activated(self, reason):
        if reason == QSystemTrayIcon.Trigger:
            self._toggle_widget()

    def _quit(self):
        from PySide6.QtWidgets import QApplication
        QApplication.instance().quit()
```

- [ ] **Step 2: Commit**

```bash
git add tray.py
git commit -m "feat: add system tray with menu and settings integration"
```

---

### Task 6: Main Entry Point

**Files:**
- Create: `deepseek-balance-widget/main.py`

- [ ] **Step 1: Implement main.py**

```python
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

    # System tray
    tray = TrayManager(widget, config, refresh_callback=refresh)

    widget.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Commit**

```bash
git add main.py
git commit -m "feat: add main entry point wiring all components"
```

---

### Task 7: Manual Verification

- [ ] **Step 1: Run the app**

Run: `cd deepseek-balance-widget && python main.py`
Expected: Settings dialog appears → enter API key → floating panel appears with balance

- [ ] **Step 2: Verify tray**

Check: System tray shows DeepSeek icon → right-click shows menu → Settings reopens dialog

- [ ] **Step 3: Verify drag**

Check: Click and drag the floating panel → moves on screen

- [ ] **Step 4: Verify error handling**

Check: Temporarily set invalid API key → panel shows "ERROR" with "invalid API key" message

---

### Task 8: PyInstaller Build Script

**Files:**
- Create: `deepseek-balance-widget/build.py`

- [ ] **Step 1: Implement build.py**

```python
# build.py
import subprocess
import sys
from pathlib import Path

spec_content = """# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=['PySide6.QtNetwork'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='DeepSeek-Balance-Widget',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
"""

def build():
    root = Path(__file__).parent
    spec_path = root / "DeepSeekBalance.spec"
    spec_path.write_text(spec_content)

    subprocess.run(
        [sys.executable, "-m", "PyInstaller", str(spec_path), "--distpath", str(root / "dist")],
        cwd=str(root),
        check=True,
    )
    print(f"Build complete: {root / 'dist' / 'DeepSeek-Balance-Widget.exe'}")

if __name__ == "__main__":
    build()
```

- [ ] **Step 2: Commit**

```bash
git add build.py
git commit -m "feat: add PyInstaller build script"
```

---

### Task 9: Final Verification & Edge Cases

- [ ] **Step 1: Run full test suite**

Run: `cd deepseek-balance-widget && python -m pytest tests/ -v`
Expected: ALL PASS

- [ ] **Step 2: Verify app with missing config**

Run: Delete `~/.deepseek-widget/config.json`, run app
Expected: Settings dialog appears, creates new config

- [ ] **Step 3: Verify app with existing config**

Run: `cd deepseek-balance-widget && python main.py`
Expected: Panel appears directly, shows balance

- [ ] **Step 4: Verify API error recovery**

Check: Unplug network → panel shows error → restore network → next refresh recovers
