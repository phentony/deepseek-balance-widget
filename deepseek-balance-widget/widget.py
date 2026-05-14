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
