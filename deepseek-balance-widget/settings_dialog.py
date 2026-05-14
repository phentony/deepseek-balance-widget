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

        self.save_btn = QPushButton("Save")
        self.save_btn.setDefault(True)
        self.save_btn.clicked.connect(self.accept)
        btn_layout.addWidget(self.save_btn)

        layout.addLayout(btn_layout)

        self.key_input.textChanged.connect(self._validate)
        self._validate()

    def _validate(self):
        has_key = bool(self.key_input.text().strip())
        self.save_btn.setEnabled(has_key)
        if not has_key:
            self.key_input.setStyleSheet("border: 1px solid #f38ba8;")
        else:
            self.key_input.setStyleSheet("")

    def get_api_key(self):
        return self.key_input.text().strip()

    def get_refresh_interval(self):
        return self.interval_input.value()
