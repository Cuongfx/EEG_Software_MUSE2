from __future__ import annotations

import threading
import time
from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import QTimer, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QPalette
from PyQt6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)

from EEG_APP import (
    AppConfig,
    ArchitectureAgent,
    MuseDevice,
    MuseDeviceManager,
    MuseStreamController,
    SessionState,
    SignalProcessor,
)
from EEG_APP.processing import estimate_hr_from_ppg, filter_eeg_for_display
from GAME import GameRegistry
from UI.dialogs import DeviceSelectionDialog
from UI.widgets import MetricCard, PlotCard


class ModernMuseWindow(QMainWindow):
    status_message = pyqtSignal(str)
    connect_completed = pyqtSignal(object, object)
    disconnect_completed = pyqtSignal(object, object)
    game_launch_completed = pyqtSignal(object, object)
    game_command_received = pyqtSignal(str)

    def __init__(self, config: AppConfig | None = None) -> None:
        super().__init__()
        self.config = config or AppConfig()
        self.project_root = Path(__file__).resolve().parent.parent
        self.architecture_agent = ArchitectureAgent()
        self.state = SessionState(self.config)
        self.processor = SignalProcessor(self.config, self.state)
        self.controller = MuseStreamController(
            self.config,
            self.state,
            self.processor,
            status_sink=self.status_message.emit,
        )
        self.device_manager = MuseDeviceManager(
            log_sink=self.status_message.emit,
            muselsl_retries=self.config.muselsl_retries,
            restart_delay_seconds=self.config.muselsl_restart_delay_seconds,
        )
        self.game_registry = GameRegistry(self.project_root)

        self.status_message.connect(self._append_log)
        self.connect_completed.connect(self._finish_connect_device)
        self.disconnect_completed.connect(self._finish_disconnect_device)
        self.game_launch_completed.connect(self._finish_game_launch)
        self.game_command_received.connect(self._handle_game_command)

        self.connection_busy = False
        self.last_saved_text = "No recording saved yet"
        self.pending_game_auto_record = False
        self.launched_games: list[dict[str, object]] = []
        self.plot_cards: list[PlotCard] = []
        self.metric_cards: dict[str, MetricCard] = {}
        self.timer = QTimer(self)

        self._setup_window()
        self._build_ui()
        self._connect_events()
        self.timer.start(self.config.plot_update_interval_ms)

    def _setup_window(self) -> None:
        self.setWindowTitle("EEG Analyse")
        self.resize(1540, 980)
        self.setMinimumSize(1340, 860)
        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Window, QColor("#f5efe6"))
        palette.setColor(QPalette.ColorRole.WindowText, QColor("#1f2937"))
        palette.setColor(QPalette.ColorRole.Base, QColor("#fffdf8"))
        palette.setColor(QPalette.ColorRole.Text, QColor("#1f2937"))
        self.setPalette(palette)
        self.setStyleSheet(
            """
            QWidget#Root {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 1,
                    stop: 0 #faf6ef,
                    stop: 0.55 #f7fbfc,
                    stop: 1 #eef7f5
                );
            }
            QFrame#HeroCard {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 #1f2937,
                    stop: 0.5 #134e4a,
                    stop: 1 #0f766e
                );
                border-radius: 30px;
            }
            QFrame#SidebarCard, QFrame#MetricCard, QFrame#PlotCard {
                background: rgba(255, 252, 246, 0.96);
                border: 1px solid #e8dccb;
                border-radius: 24px;
            }
            QLabel#HeroTitle {
                color: #fff8ee;
                font-size: 30px;
                font-weight: 800;
            }
            QLabel#HeroSubtitle {
                color: rgba(255, 248, 238, 0.84);
                font-size: 13px;
            }
            QLabel#SectionTitle, QLabel#DialogTitle {
                color: #111827;
                font-size: 15px;
                font-weight: 800;
            }
            QLabel#DialogText, QLabel#DialogStatus, QLabel#SupportText {
                color: #5b6472;
                font-size: 12px;
            }
            QLabel#MetricTitle {
                color: #6b7280;
                font-size: 11px;
                font-weight: 700;
            }
            QLabel#MetricValue {
                font-size: 22px;
                font-weight: 900;
            }
            QLabel#MetricCaption {
                color: #6b7280;
                font-size: 11px;
            }
            QPushButton#PrimaryButton {
                background: #0f766e;
                color: white;
                border: none;
                border-radius: 16px;
                padding: 12px 18px;
                font-weight: 800;
            }
            QPushButton#PrimaryButton:hover {
                background: #115e59;
            }
            QPushButton#AccentButton {
                background: #f97316;
                color: white;
                border: none;
                border-radius: 16px;
                padding: 12px 18px;
                font-weight: 800;
            }
            QPushButton#AccentButton:hover {
                background: #ea580c;
            }
            QPushButton#SecondaryButton {
                background: #fffdf8;
                color: #1f2937;
                border: 1px solid #d9c6ae;
                border-radius: 16px;
                padding: 12px 18px;
                font-weight: 700;
            }
            QPushButton#SecondaryButton:hover {
                background: #fff5ea;
            }
            QPushButton:disabled {
                background: #e7dfd5;
                color: #9ca3af;
                border-color: #e7dfd5;
            }
            QPlainTextEdit#LogOutput, QListWidget {
                background: #fffdf9;
                color: #1f2937;
                border: 1px solid #eadfce;
                border-radius: 18px;
                padding: 12px;
                font-size: 12px;
            }
            QComboBox {
                background: #fffdf8;
                border: 1px solid #d9c6ae;
                border-radius: 16px;
                padding: 10px 12px;
                font-size: 12px;
            }
            """
        )

    def _build_ui(self) -> None:
        root = QWidget()
        root.setObjectName("Root")
        self.setCentralWidget(root)

        page = QVBoxLayout(root)
        page.setContentsMargins(28, 24, 28, 24)
        page.setSpacing(20)
        page.addWidget(self._build_header())

        main_row = QHBoxLayout()
        main_row.setSpacing(20)
        page.addLayout(main_row, stretch=1)
        main_row.addWidget(self._build_signal_area(), stretch=5)
        main_row.addWidget(self._build_control_area(), stretch=3)

    def _build_header(self) -> QFrame:
        card = QFrame()
        card.setObjectName("HeroCard")
        layout = QHBoxLayout(card)
        layout.setContentsMargins(26, 24, 26, 24)
        layout.setSpacing(22)

        text_column = QVBoxLayout()
        title = QLabel("EEG Analyse")
        title.setObjectName("HeroTitle")
        subtitle = QLabel(
            "Designed by CuongFX"
        )
        subtitle.setObjectName("HeroSubtitle")
        subtitle.setWordWrap(True)
        text_column.addWidget(title)
        text_column.addWidget(subtitle)

        badge_column = QVBoxLayout()
        badge_column.setSpacing(10)
        self.session_badge = QLabel("Idle")
        self.recording_badge = QLabel("Not Recording")
        self._set_badge_style(self.session_badge, active=False, accent="teal")
        self._set_badge_style(self.recording_badge, active=False, accent="orange")
        badge_column.addWidget(self.session_badge)
        badge_column.addWidget(self.recording_badge)
        badge_column.addStretch(1)

        layout.addLayout(text_column, stretch=1)
        layout.addLayout(badge_column)
        return card

    def _build_signal_area(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(18)

        metric_grid = QGridLayout()
        metric_grid.setHorizontalSpacing(14)
        metric_grid.setVerticalSpacing(14)
        self.metric_cards["connection"] = MetricCard("Connection", "#0f766e")
        self.metric_cards["recording"] = MetricCard("Recording", "#f97316")
        self.metric_cards["battery"] = MetricCard("Battery", "#dc2626")
        self.metric_cards["hr"] = MetricCard("Heart Rate", "#1d4ed8")
        metric_grid.addWidget(self.metric_cards["connection"], 0, 0)
        metric_grid.addWidget(self.metric_cards["recording"], 0, 1)
        metric_grid.addWidget(self.metric_cards["battery"], 0, 2)
        metric_grid.addWidget(self.metric_cards["hr"], 0, 3)
        layout.addLayout(metric_grid)

        plot_grid = QGridLayout()
        plot_grid.setHorizontalSpacing(16)
        plot_grid.setVerticalSpacing(16)
        for index, channel in enumerate(self.config.eeg_channels):
            card = PlotCard(channel.name, self.config.eeg_colors[index], self.config.eeg_plot_range_uv)
            self.plot_cards.append(card)
            plot_grid.addWidget(card, index // 2, index % 2)
        ppg_card = PlotCard("PPG (RED - LUX, bandpassed)", "#7c3aed", self.config.ppg_plot_range)
        self.plot_cards.append(ppg_card)
        ppg_row = (self.config.eeg_channel_count + 1) // 2
        plot_grid.addWidget(ppg_card, ppg_row, 0, 1, 2)
        layout.addLayout(plot_grid, stretch=1)
        return container

    def _build_control_area(self) -> QWidget:
        sidebar = QWidget()
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        layout.addWidget(self._build_device_card())
        layout.addWidget(self._build_game_card())
        layout.addWidget(self._build_log_card(), stretch=1)
        return sidebar

    def _build_device_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("SidebarCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(22, 22, 22, 22)
        layout.setSpacing(12)

        title = QLabel("Device + Recording")
        title.setObjectName("SectionTitle")
        layout.addWidget(title)

        button_row = QHBoxLayout()
        self.connect_button = QPushButton("Connect to Device")
        self.connect_button.setObjectName("PrimaryButton")
        self.disconnect_button = QPushButton("Disconnect Device")
        self.disconnect_button.setObjectName("SecondaryButton")
        button_row.addWidget(self.connect_button)
        button_row.addWidget(self.disconnect_button)
        layout.addLayout(button_row)

        self.record_button = QPushButton("Record Data")
        self.record_button.setObjectName("AccentButton")
        layout.addWidget(self.record_button)

        self.device_label = QLabel("Selected device: none")
        self.device_label.setObjectName("SupportText")
        self.device_label.setWordWrap(True)
        layout.addWidget(self.device_label)

        self.eeg_status_label = QLabel()
        self.ppg_status_label = QLabel()
        self._set_stream_label(self.eeg_status_label, "EEG", False)
        self._set_stream_label(self.ppg_status_label, "PPG", False)
        layout.addWidget(self.eeg_status_label)
        layout.addWidget(self.ppg_status_label)

        self.last_save_label = QLabel("Last save: No recording saved yet")
        self.last_save_label.setObjectName("SupportText")
        self.last_save_label.setWordWrap(True)
        layout.addWidget(self.last_save_label)

        rules = ", ".join(rule.name for rule in self.architecture_agent.list_rules())
        self.rules_label = QLabel(f"Architecture rules: {rules}")
        self.rules_label.setObjectName("SupportText")
        self.rules_label.setWordWrap(True)
        layout.addWidget(self.rules_label)
        return card

    def _build_game_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("SidebarCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(22, 22, 22, 22)
        layout.setSpacing(12)

        title = QLabel("Games")
        title.setObjectName("SectionTitle")
        layout.addWidget(title)

        self.game_combo = QComboBox()
        for game in self.game_registry.list_games():
            self.game_combo.addItem(game.title, game.game_id)
        layout.addWidget(self.game_combo)

        self.game_description_label = QLabel()
        self.game_description_label.setObjectName("SupportText")
        self.game_description_label.setWordWrap(True)
        layout.addWidget(self.game_description_label)

        self.launch_game_button = QPushButton("Start Game")
        self.launch_game_button.setObjectName("SecondaryButton")
        layout.addWidget(self.launch_game_button)

        auto_note = QLabel(
            "Starting a game will automatically begin recording if a device is already connected and recording is not active."
        )
        auto_note.setObjectName("SupportText")
        auto_note.setWordWrap(True)
        layout.addWidget(auto_note)

        self._update_game_description()
        return card

    def _build_log_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("SidebarCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(22, 22, 22, 22)
        layout.setSpacing(12)

        title = QLabel("Session Log")
        title.setObjectName("SectionTitle")
        self.log_output = QPlainTextEdit()
        self.log_output.setObjectName("LogOutput")
        self.log_output.setReadOnly(True)
        self.log_output.setPlaceholderText("Connection events, recording state, and game launches appear here.")
        layout.addWidget(title)
        layout.addWidget(self.log_output)
        return card

    def _connect_events(self) -> None:
        self.connect_button.clicked.connect(self._open_device_dialog)
        self.disconnect_button.clicked.connect(self._disconnect_async)
        self.record_button.clicked.connect(self._toggle_recording)
        self.launch_game_button.clicked.connect(self._launch_selected_game_async)
        self.game_combo.currentIndexChanged.connect(self._update_game_description)
        self.timer.timeout.connect(self._refresh_ui)

    def _open_device_dialog(self) -> None:
        if self.connection_busy:
            return
        dialog = DeviceSelectionDialog(self.device_manager.scan_devices, self)
        if dialog.exec() == DeviceSelectionDialog.DialogCode.Accepted and dialog.selected_device is not None:
            self._connect_device_async(dialog.selected_device)

    def _connect_device_async(self, device: MuseDevice) -> None:
        self.connection_busy = True
        self._append_log(f"Connecting to {device.display_name}...")
        threading.Thread(target=self._connect_worker, args=(device,), daemon=True).start()

    def _connect_worker(self, device: MuseDevice) -> None:
        try:
            self._disconnect_internal(save_recording=True)
            self.device_manager.read_battery_percentage(device)
            self.device_manager.connect(device, include_ppg=True)
            time.sleep(self.config.device_warmup_seconds)
            self.controller.start()
            self.connect_completed.emit(device, None)
        except Exception as exc:
            self.device_manager.disconnect()
            self.connect_completed.emit(None, str(exc))

    def _finish_connect_device(self, device: MuseDevice | None, error: str | None) -> None:
        self.connection_busy = False
        if error:
            self._append_log(f"Connection failed: {error}")
            QMessageBox.warning(
                self,
                "Connect to Device",
                f"Could not connect to the selected device.\n\n{error}",
            )
            return
        if device is not None:
            self._append_log(f"Connected to {device.display_name}")

    def _disconnect_async(self) -> None:
        if self.connection_busy:
            return
        self.connection_busy = True
        self._append_log("Disconnecting device...")
        threading.Thread(target=self._disconnect_worker, daemon=True).start()

    def _disconnect_worker(self) -> None:
        try:
            saved_files = self._disconnect_internal(save_recording=True)
            self.disconnect_completed.emit(saved_files, None)
        except Exception as exc:
            self.disconnect_completed.emit(None, str(exc))

    def _disconnect_internal(self, *, save_recording: bool):
        saved_files = None
        if self.state.recording_enabled:
            saved_files = self.controller.stop_recording(save=save_recording)
        if self.controller.running or self.controller.eeg_inlet is not None or self.controller.ppg_inlet is not None:
            self.controller.stop(save=False)
        self.device_manager.disconnect()
        return saved_files

    def _finish_disconnect_device(self, saved_files, error: str | None) -> None:
        self.connection_busy = False
        if error:
            self._append_log(f"Disconnect failed: {error}")
            QMessageBox.warning(self, "Disconnect Device", f"Could not disconnect the device.\n\n{error}")
            return
        if saved_files is None:
            self._append_log("Device disconnected.")

    def _toggle_recording(self) -> None:
        status = self.controller.status()
        if not status.running:
            QMessageBox.information(
                self,
                "Record Data",
                "Connect a device first. Recording only works after a Muse stream is connected.",
            )
            return

        if status.recording:
            saved_files = self.controller.stop_recording(save=True)
            if saved_files is not None:
                self._append_log("Manual recording session saved.")
        else:
            self.controller.start_recording()

    def _launch_selected_game_async(self) -> None:
        game_id = self.game_combo.currentData()
        if game_id is None:
            return

        status = self.controller.status()
        self.pending_game_auto_record = False
        if not status.running:
            QMessageBox.information(
                self,
                "Start Game",
                "The game will open, but EEG/PPG recording commands will be ignored because no device is connected.",
            )

        self.launch_game_button.setEnabled(False)
        threading.Thread(target=self._launch_game_worker, args=(game_id,), daemon=True).start()

    def _launch_game_worker(self, game_id: str) -> None:
        try:
            process = self.game_registry.launch(game_id)
            self.game_launch_completed.emit(game_id, process)
        except Exception as exc:
            self.game_launch_completed.emit(game_id, str(exc))

    def _finish_game_launch(self, game_id: str, result) -> None:
        self.launch_game_button.setEnabled(True)
        if isinstance(result, str):
            if self.pending_game_auto_record and self.controller.status().recording:
                self.controller.stop_recording(save=True)
            self._append_log(f"Could not launch game: {result}")
            QMessageBox.warning(self, "Start Game", f"Could not launch the selected game.\n\n{result}")
            self.pending_game_auto_record = False
            return

        self.launched_games.append(
            {
                "process": result,
                "title": self.game_registry.get(game_id).title,
                "auto_record": self.pending_game_auto_record,
            }
        )
        threading.Thread(target=self._monitor_game_output, args=(result,), daemon=True).start()
        self.pending_game_auto_record = False
        self._append_log(f"Launched {self.game_registry.get(game_id).title} in a separate game window.")

    def _monitor_game_output(self, process) -> None:
        if process.stdout is None:
            return
        try:
            for raw_line in process.stdout:
                message = raw_line.strip()
                if not message:
                    continue
                if message.startswith("EEG_CMD:"):
                    self.game_command_received.emit(message.removeprefix("EEG_CMD:"))
                else:
                    self.status_message.emit(f"[game] {message}")
        except Exception as exc:
            self.status_message.emit(f"Game output monitor stopped unexpectedly: {exc}")

    def _refresh_ui(self) -> None:
        status = self.controller.status()
        current_device = self.device_manager.current_device

        self._set_badge_style(self.session_badge, active=status.running, accent="teal")
        self.session_badge.setText("Device Connected" if status.running else "Disconnected")
        self._set_badge_style(self.recording_badge, active=status.recording, accent="orange")
        self.recording_badge.setText("Recording" if status.recording else "Not Recording")

        self.connect_button.setEnabled(not self.connection_busy)
        self.disconnect_button.setEnabled((status.running or self.device_manager.is_connected()) and not self.connection_busy)
        self.record_button.setEnabled(not self.connection_busy)
        self.record_button.setText("Stop Recording" if status.recording else "Record Data")

        self.device_label.setText(
            f"Selected device: {current_device.display_name}" if current_device else "Selected device: none"
        )
        self._set_stream_label(self.eeg_status_label, "EEG", status.eeg_connected)
        self._set_stream_label(self.ppg_status_label, "PPG", status.ppg_connected)

        with self.state.data_lock:
            eeg_series = [list(buffer) for buffer in self.state.eeg_raw_buffers]
            ppg_series = list(self.state.ppg_filtered_buffer)
            hr_series = list(self.state.heart_rate_buffer)

        for index, values in enumerate(eeg_series):
            display_values = values
            if len(values) > 10:
                try:
                    display_values = list(
                        filter_eeg_for_display(values, self.config.eeg_sampling_rate)
                    )
                except Exception as exc:
                    self._append_log(f"EEG display filter fallback on {self.config.eeg_channels[index].name}: {exc}")
            auto_scale = self.config.eeg_channels[index].name == "AUX"
            self.plot_cards[index].canvas.update_series(
                display_values,
                self.config.max_points,
                auto_scale=auto_scale,
                min_half_range=15.0 if auto_scale else 20.0,
            )
        self.plot_cards[-1].canvas.update_series(ppg_series, self.config.max_points)

        bpm = hr_series[-1] if hr_series else estimate_hr_from_ppg(ppg_series, self.config.ppg_sampling_rate)
        battery = self.device_manager.current_battery_percent
        self.metric_cards["connection"].set_value("Live" if status.running else "Offline", "Stream state")
        self.metric_cards["recording"].set_value("REC" if status.recording else "Standby", "Capture mode")
        self.metric_cards["battery"].set_value(
            f"{battery:.0f}%" if battery is not None else "--%",
            "Device battery" if battery is not None else "Battery unavailable",
        )
        self.metric_cards["hr"].set_value(f"{bpm:.1f} bpm" if bpm is not None else "-- bpm", "Latest estimate")
        self.last_save_label.setText(f"Last save: {self.last_saved_text}")

        self._prune_finished_games()

    def _update_game_description(self) -> None:
        game_id = self.game_combo.currentData()
        if game_id is None:
            self.game_description_label.setText("No game selected.")
            return
        game = self.game_registry.get(game_id)
        details = [game.description]
        if game.source:
            details.append(game.source)
        self.game_description_label.setText("\n\n".join(details))

    def _append_log(self, message: str) -> None:
        stamp = datetime.now().strftime("%H:%M:%S")
        self.log_output.appendPlainText(f"[{stamp}] {message}")
        if message.startswith("Saved to "):
            self.last_saved_text = message.removeprefix("Saved to ")

    def _handle_game_command(self, command: str) -> None:
        if command == "START_RECORDING":
            status = self.controller.status()
            if not status.running:
                self._append_log("Game requested recording, but no device stream is connected.")
                return
            if not status.recording:
                self.controller.start_recording()
                self._append_log("Recording started from the Focus Game block.")
            return

        if command == "STOP_RECORDING":
            status = self.controller.status()
            if status.recording:
                saved_files = self.controller.stop_recording(save=True)
                if saved_files is not None:
                    self._append_log("Recording stopped automatically at block end.")
            return

        if command.startswith("LOG:"):
            self._append_log(command.removeprefix("LOG:"))
            return

        self._append_log(f"Unknown game command: {command}")

    def _prune_finished_games(self) -> None:
        remaining = []
        for launched in self.launched_games:
            process = launched["process"]
            if process.poll() is None:
                remaining.append(launched)
                continue

            title = launched["title"]
            self._append_log(f"{title} window closed.")
            if self.controller.status().recording:
                saved_files = self.controller.stop_recording(save=True)
                if saved_files is not None:
                    self._append_log("Recording stopped automatically because the game session ended.")
        self.launched_games = remaining

    def _set_stream_label(self, label: QLabel, name: str, connected: bool) -> None:
        color = "#065f46" if connected else "#92400e"
        background = "#ecfdf5" if connected else "#fff7ed"
        border = "#a7f3d0" if connected else "#fed7aa"
        label.setText(f"{name} Stream  {'Connected' if connected else 'Waiting'}")
        label.setStyleSheet(
            f"""
            QLabel {{
                color: {color};
                background: {background};
                border: 1px solid {border};
                border-radius: 14px;
                padding: 10px 12px;
                font-weight: 700;
            }}
            """
        )

    def _set_badge_style(self, label: QLabel, *, active: bool, accent: str) -> None:
        if accent == "orange":
            color = "#9a3412" if active else "#7c2d12"
            background = "#ffedd5" if active else "#fff7ed"
            border = "#fdba74" if active else "#fed7aa"
        else:
            color = "#064e3b" if active else "#134e4a"
            background = "#d1fae5" if active else "#ccfbf1"
            border = "#6ee7b7" if active else "#99f6e4"
        label.setStyleSheet(
            f"""
            QLabel {{
                color: {color};
                background: {background};
                border: 1px solid {border};
                border-radius: 18px;
                padding: 10px 18px;
                font-size: 13px;
                font-weight: 800;
            }}
            """
        )

    def closeEvent(self, event) -> None:  # noqa: N802
        try:
            self._disconnect_internal(save_recording=True)
        except Exception:
            pass
        super().closeEvent(event)
