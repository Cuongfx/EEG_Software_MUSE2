from __future__ import annotations

import threading

from PyQt6.QtCore import QTimer, Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from EEG_APP.device import MuseDevice


class DeviceSelectionDialog(QDialog):
    scan_completed = pyqtSignal(object)
    scan_failed = pyqtSignal(str)

    def __init__(self, scan_callback, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.scan_callback = scan_callback
        self.selected_device: MuseDevice | None = None
        self.setWindowTitle("Connect to Device")
        self.setMinimumSize(560, 420)
        self._build_ui()
        self.scan_completed.connect(self._populate_devices)
        self.scan_failed.connect(self._show_scan_error)
        QTimer.singleShot(0, self.scan_devices)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 22, 22, 22)
        layout.setSpacing(14)

        title = QLabel("Available Muse Devices")
        title.setObjectName("DialogTitle")
        description = QLabel(
            "Click scan to search nearby Muse headsets, then choose one device to connect."
        )
        description.setObjectName("DialogText")
        description.setWordWrap(True)

        self.status_label = QLabel("Scanning for devices...")
        self.status_label.setObjectName("DialogStatus")
        self.device_list = QListWidget()
        self.device_list.itemDoubleClicked.connect(lambda _item: self._accept_selection())

        buttons = QHBoxLayout()
        self.scan_button = QPushButton("Scan Again")
        self.connect_button = QPushButton("Connect")
        cancel_button = QPushButton("Cancel")
        self.scan_button.clicked.connect(self.scan_devices)
        self.connect_button.clicked.connect(self._accept_selection)
        cancel_button.clicked.connect(self.reject)
        buttons.addWidget(self.scan_button)
        buttons.addStretch(1)
        buttons.addWidget(cancel_button)
        buttons.addWidget(self.connect_button)

        layout.addWidget(title)
        layout.addWidget(description)
        layout.addWidget(self.status_label)
        layout.addWidget(self.device_list, stretch=1)
        layout.addLayout(buttons)

    def scan_devices(self) -> None:
        self.status_label.setText("Scanning for devices...")
        self.scan_button.setEnabled(False)
        self.connect_button.setEnabled(False)
        self.device_list.clear()
        threading.Thread(target=self._scan_worker, daemon=True).start()

    def _scan_worker(self) -> None:
        try:
            devices = self.scan_callback()
            self.scan_completed.emit(devices)
        except Exception as exc:
            self.scan_failed.emit(str(exc))

    def _populate_devices(self, devices: list[MuseDevice]) -> None:
        self.device_list.clear()
        if not devices:
            self.status_label.setText("No Muse devices were found.")
        else:
            self.status_label.setText(f"Found {len(devices)} device(s). Select one to connect.")
            for device in devices:
                item = QListWidgetItem(device.display_name)
                item.setData(Qt.ItemDataRole.UserRole, device)
                self.device_list.addItem(item)
            self.device_list.setCurrentRow(0)
            self.connect_button.setEnabled(True)
        self.scan_button.setEnabled(True)

    def _show_scan_error(self, message: str) -> None:
        self.scan_button.setEnabled(True)
        self.status_label.setText(f"Scan failed: {message}")

    def _accept_selection(self) -> None:
        item = self.device_list.currentItem()
        if item is None:
            QMessageBox.information(self, "Connect to Device", "Please select a device first.")
            return
        self.selected_device = item.data(Qt.ItemDataRole.UserRole)
        self.accept()
