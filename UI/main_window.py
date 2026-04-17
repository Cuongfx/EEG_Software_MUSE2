from __future__ import annotations

import threading
import time
from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import QTimer, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QPalette
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QScrollArea,
    QPushButton,
    QPlainTextEdit,
    QSizePolicy,
    QSplitter,
    QTabWidget,
    QTextEdit,
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
from GAME import ExaminerPreview
from GAME import GameRegistry
from UI.dialogs import DeviceSelectionDialog
from UI.widgets import MetricCard, PlotCard


class ModernMuseWindow(QMainWindow):
    status_message = pyqtSignal(str)
    connect_completed = pyqtSignal(object, object)
    disconnect_completed = pyqtSignal(object, object)
    game_launch_completed = pyqtSignal(object, object)
    game_command_received = pyqtSignal(str)

    UI_TRANSLATIONS = {
        "en": {
            "window_title": "EEG Analyse",
            "tab_analyse": "Analyse",
            "tab_experiment": "Experiment Set-Up",
            "hero_title": "EEG Analyse",
            "hero_subtitle": "Designed by CuongFX",
            "idle": "Idle",
            "disconnected": "Disconnected",
            "connected": "Device Connected",
            "recording_off": "Not Recording",
            "recording_on": "Recording",
            "metric_connection": "Connection",
            "metric_recording": "Recording",
            "metric_battery": "Battery",
            "metric_hr": "Heart Rate",
            "metric_stream_state": "Stream state",
            "metric_capture_mode": "Capture mode",
            "metric_device_battery": "Device battery",
            "metric_battery_unavailable": "Battery unavailable",
            "metric_latest_estimate": "Latest estimate",
            "metric_live": "Live",
            "metric_offline": "Offline",
            "metric_standby": "Standby",
            "device_title": "Device + Recording",
            "connect_device": "Connect to Device",
            "disconnect_device": "Disconnect Device",
            "record_data": "Record Data",
            "stop_recording": "Stop Recording",
            "selected_device_none": "Selected device: none",
            "last_save_none": "No recording saved yet",
            "last_save_prefix": "Last save: ",
            "rules_prefix": "Architecture rules: {rules}",
            "games_title": "Games",
            "game_language_prefix": "Game language: {languages}",
            "start_game": "Start Game",
            "play_demo": "Play Demo",
            "game_auto_note": "Starting a game will automatically begin recording if a device is already connected and recording is not active.",
            "session_log": "Session Log",
            "session_log_placeholder": "Connection events, recording state, and game launches appear here.",
            "examiner_control": "Examiner Control",
            "examiner_empty": "No examiner control available.",
            "examiner_default_subtitle": "Configure the participant and session details before launching the game.",
            "field_name": "Name",
            "field_id": "ID",
            "field_age": "Age",
            "field_n_value": "N Value",
            "field_note": "Note",
            "field_relax_audio": "Play alpha audio during Relax",
            "planner_title": "Session Planner",
            "planner_session": "Session",
            "planner_order": "Order",
            "planner_duration": "Duration (minutes)",
            "stage_relax": "Relax",
            "stage_break": "Break",
            "stage_game": "Game",
            "planner_help": "Use order 1, 2, and 3 exactly once. Set any stage duration to 0 if you want to skip that stage, but Game must be greater than 0.",
            "examiner_language": "Language: {language}",
            "stream_connected": "{name} Stream  Connected",
            "stream_waiting": "{name} Stream  Waiting",
            "no_game_selected": "No game selected.",
            "no_device_recording": "Connect a device first. Recording only works after a Muse stream is connected.",
            "record_data_title": "Record Data",
            "start_game_title": "Start Game",
            "start_game_no_device": "The game will open, but EEG/PPG recording commands will be ignored because no device is connected.",
            "connect_device_title": "Connect to Device",
            "disconnect_device_title": "Disconnect Device",
            "connect_device_failed": "Could not connect to the selected device.\n\n{error}",
            "disconnect_device_failed": "Could not disconnect the device.\n\n{error}",
            "name_required": "Name is required.",
            "id_required": "ID is required.",
            "age_required": "Age is required.",
            "n_value_required": "N value is required.",
            "n_value_integer": "N value must be a whole number.",
            "n_value_positive": "N value must be at least 1.",
            "order_whole_number": "{stage} order must be a whole number.",
            "duration_number": "{stage} duration must be a number.",
            "order_range": "{stage} order must be 1, 2, or 3.",
            "duration_negative": "{stage} duration can not be negative.",
            "order_unique": "Relax, Break, and Game must use order 1, 2, and 3 exactly once.",
            "game_duration_positive": "Game duration must be greater than zero.",
        },
        "de": {
            "window_title": "EEG Analyse",
            "tab_analyse": "Analyse",
            "tab_experiment": "Experiment-Setup",
            "hero_title": "EEG Analyse",
            "hero_subtitle": "Entwickelt von CuongFX",
            "idle": "Leerlauf",
            "disconnected": "Getrennt",
            "connected": "Gerät verbunden",
            "recording_off": "Keine Aufnahme",
            "recording_on": "Aufnahme",
            "metric_connection": "Verbindung",
            "metric_recording": "Aufnahme",
            "metric_battery": "Batterie",
            "metric_hr": "Herzfrequenz",
            "metric_stream_state": "Stream-Status",
            "metric_capture_mode": "Aufnahmemodus",
            "metric_device_battery": "Gerätebatterie",
            "metric_battery_unavailable": "Batterie nicht verfügbar",
            "metric_latest_estimate": "Letzte Schätzung",
            "metric_live": "Live",
            "metric_offline": "Offline",
            "metric_standby": "Bereit",
            "device_title": "Gerät + Aufnahme",
            "connect_device": "Gerät verbinden",
            "disconnect_device": "Gerät trennen",
            "record_data": "Daten aufnehmen",
            "stop_recording": "Aufnahme stoppen",
            "selected_device_none": "Gewähltes Gerät: keines",
            "last_save_none": "Noch keine Aufnahme gespeichert",
            "last_save_prefix": "Letzte Speicherung: ",
            "rules_prefix": "Architekturregeln: {rules}",
            "games_title": "Spiele",
            "game_language_prefix": "Spielsprache: {languages}",
            "start_game": "Spiel starten",
            "play_demo": "Demo spielen",
            "game_auto_note": "Beim Start eines Spiels beginnt die Aufnahme automatisch, wenn bereits ein Gerät verbunden ist und noch nicht aufgenommen wird.",
            "session_log": "Sitzungsprotokoll",
            "session_log_placeholder": "Verbindungsereignisse, Aufnahmestatus und Spielstarts erscheinen hier.",
            "examiner_control": "Leitersteuerung",
            "examiner_empty": "Keine Leitersteuerung verfügbar.",
            "examiner_default_subtitle": "Konfigurieren Sie Teilnehmer- und Sitzungsdaten vor dem Start des Spiels.",
            "field_name": "Name",
            "field_id": "ID",
            "field_age": "Alter",
            "field_n_value": "N-Wert",
            "field_note": "Notiz",
            "field_relax_audio": "Alpha-Audio waehrend Entspannung abspielen",
            "planner_title": "Sitzungsplaner",
            "planner_session": "Sitzung",
            "planner_order": "Reihenfolge",
            "planner_duration": "Dauer (Minuten)",
            "stage_relax": "Entspannung",
            "stage_break": "Pause",
            "stage_game": "Spiel",
            "planner_help": "Verwenden Sie 1, 2 und 3 jeweils genau einmal. Eine Dauer von 0 überspringt die Stufe, aber Spiel muss größer als 0 sein.",
            "examiner_language": "Sprache: {language}",
            "stream_connected": "{name}-Stream  Verbunden",
            "stream_waiting": "{name}-Stream  Wartet",
            "no_game_selected": "Kein Spiel ausgewählt.",
            "no_device_recording": "Verbinden Sie zuerst ein Gerät. Aufnehmen funktioniert erst nach einem verbundenen Muse-Stream.",
            "record_data_title": "Daten aufnehmen",
            "start_game_title": "Spiel starten",
            "start_game_no_device": "Das Spiel wird geöffnet, aber EEG/PPG-Aufnahmebefehle werden ignoriert, weil kein Gerät verbunden ist.",
            "connect_device_title": "Gerät verbinden",
            "disconnect_device_title": "Gerät trennen",
            "connect_device_failed": "Das ausgewählte Gerät konnte nicht verbunden werden.\n\n{error}",
            "disconnect_device_failed": "Das Gerät konnte nicht getrennt werden.\n\n{error}",
            "name_required": "Name ist erforderlich.",
            "id_required": "ID ist erforderlich.",
            "age_required": "Alter ist erforderlich.",
            "n_value_required": "N-Wert ist erforderlich.",
            "n_value_integer": "Der N-Wert muss eine ganze Zahl sein.",
            "n_value_positive": "Der N-Wert muss mindestens 1 sein.",
            "order_whole_number": "Die Reihenfolge für {stage} muss eine ganze Zahl sein.",
            "duration_number": "Die Dauer für {stage} muss eine Zahl sein.",
            "order_range": "Die Reihenfolge für {stage} muss 1, 2 oder 3 sein.",
            "duration_negative": "Die Dauer für {stage} darf nicht negativ sein.",
            "order_unique": "Entspannung, Pause und Spiel müssen 1, 2 und 3 jeweils genau einmal verwenden.",
            "game_duration_positive": "Die Spieldauer muss größer als null sein.",
        },
        "vi": {
            "window_title": "EEG Analyse",
            "tab_analyse": "Phân tích",
            "tab_experiment": "Thiết lập thí nghiệm",
            "hero_title": "EEG Analyse",
            "hero_subtitle": "Thiết kế bởi CuongFX",
            "idle": "Chờ",
            "disconnected": "Ngắt kết nối",
            "connected": "Đã kết nối thiết bị",
            "recording_off": "Không ghi",
            "recording_on": "Đang ghi",
            "metric_connection": "Kết nối",
            "metric_recording": "Ghi dữ liệu",
            "metric_battery": "Pin",
            "metric_hr": "Nhịp tim",
            "metric_stream_state": "Trạng thái luồng",
            "metric_capture_mode": "Chế độ ghi",
            "metric_device_battery": "Pin thiết bị",
            "metric_battery_unavailable": "Không có dữ liệu pin",
            "metric_latest_estimate": "Ước tính mới nhất",
            "metric_live": "Trực tiếp",
            "metric_offline": "Ngoại tuyến",
            "metric_standby": "Chờ",
            "device_title": "Thiết bị + Ghi dữ liệu",
            "connect_device": "Kết nối thiết bị",
            "disconnect_device": "Ngắt thiết bị",
            "record_data": "Ghi dữ liệu",
            "stop_recording": "Dừng ghi",
            "selected_device_none": "Thiết bị đã chọn: chưa có",
            "last_save_none": "Chưa lưu bản ghi nào",
            "last_save_prefix": "Lần lưu cuối: ",
            "rules_prefix": "Quy tắc kiến trúc: {rules}",
            "games_title": "Trò chơi",
            "game_language_prefix": "Ngôn ngữ game: {languages}",
            "start_game": "Bắt đầu game",
            "play_demo": "Chạy demo",
            "game_auto_note": "Khi bắt đầu game, hệ thống sẽ tự ghi dữ liệu nếu thiết bị đã kết nối và chưa ghi.",
            "session_log": "Nhật ký phiên",
            "session_log_placeholder": "Sự kiện kết nối, trạng thái ghi và lần mở game sẽ xuất hiện tại đây.",
            "examiner_control": "Điều khiển Giám sát",
            "examiner_empty": "Không có điều khiển giám sát.",
            "examiner_default_subtitle": "Thiết lập thông tin người tham gia và phiên trước khi bắt đầu game.",
            "field_name": "Tên",
            "field_id": "ID",
            "field_age": "Tuổi",
            "field_n_value": "Giá trị N",
            "field_note": "Ghi chú",
            "field_relax_audio": "Phát âm thanh alpha trong lúc Thư giãn",
            "planner_title": "Lập kế hoạch phiên",
            "planner_session": "Phiên",
            "planner_order": "Thứ tự",
            "planner_duration": "Thời lượng (phút)",
            "stage_relax": "Thư giãn",
            "stage_break": "Nghỉ",
            "stage_game": "Game",
            "planner_help": "Dùng 1, 2 và 3 mỗi số đúng một lần. Có thể đặt thời lượng 0 để bỏ qua giai đoạn đó, nhưng Game phải lớn hơn 0.",
            "examiner_language": "Ngôn ngữ: {language}",
            "stream_connected": "Luồng {name}  Đã kết nối",
            "stream_waiting": "Luồng {name}  Đang chờ",
            "no_game_selected": "Chưa chọn game.",
            "no_device_recording": "Hãy kết nối thiết bị trước. Chỉ có thể ghi khi luồng Muse đã kết nối.",
            "record_data_title": "Ghi dữ liệu",
            "start_game_title": "Bắt đầu game",
            "start_game_no_device": "Game sẽ mở, nhưng lệnh ghi EEG/PPG sẽ bị bỏ qua vì chưa có thiết bị kết nối.",
            "connect_device_title": "Kết nối thiết bị",
            "disconnect_device_title": "Ngắt thiết bị",
            "connect_device_failed": "Không thể kết nối thiết bị đã chọn.\n\n{error}",
            "disconnect_device_failed": "Không thể ngắt thiết bị.\n\n{error}",
            "name_required": "Cần nhập tên.",
            "id_required": "Cần nhập ID.",
            "age_required": "Cần nhập tuổi.",
            "n_value_required": "Cần nhập giá trị N.",
            "n_value_integer": "Giá trị N phải là số nguyên.",
            "n_value_positive": "Giá trị N phải lớn hơn hoặc bằng 1.",
            "order_whole_number": "Thứ tự của {stage} phải là số nguyên.",
            "duration_number": "Thời lượng của {stage} phải là số.",
            "order_range": "Thứ tự của {stage} phải là 1, 2 hoặc 3.",
            "duration_negative": "Thời lượng của {stage} không được âm.",
            "order_unique": "Thư giãn, Nghỉ và Game phải dùng 1, 2 và 3, mỗi số một lần.",
            "game_duration_positive": "Thời lượng Game phải lớn hơn 0.",
        },
    }

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
        self.metric_card_widgets: list[MetricCard] = []
        self.eeg_plot_widgets: list[PlotCard] = []
        self.ppg_plot_card: PlotCard | None = None
        self.timer = QTimer(self)
        self.game_languages = {
            "en": "English",
            "de": "German",
            "vi": "Tiếng Việt",
        }
        self.software_languages = {
            "en": ("🇬🇧 English", "English"),
            "de": ("🇩🇪 Deutsch", "Deutsch"),
            "vi": ("🇻🇳 Tiếng Việt", "Tiếng Việt"),
        }
        self.software_language_code = "en"

        self._setup_window()
        self._build_ui()
        self._connect_events()
        self._apply_software_language()
        self.timer.start(self.config.plot_update_interval_ms)

    def _ui(self, key: str, **kwargs) -> str:
        text = self.UI_TRANSLATIONS.get(self.software_language_code, self.UI_TRANSLATIONS["en"]).get(
            key,
            self.UI_TRANSLATIONS["en"].get(key, key),
        )
        return text.format(**kwargs) if kwargs else text

    def _stage_label(self, stage_key: str) -> str:
        return self._ui(f"stage_{stage_key}")

    def _apply_software_language(self) -> None:
        default_last_save_values = {
            bundle["last_save_none"]
            for bundle in self.UI_TRANSLATIONS.values()
            if "last_save_none" in bundle
        }
        if self.last_saved_text in default_last_save_values:
            self.last_saved_text = self._ui("last_save_none")
        self.setWindowTitle(self._ui("window_title"))
        if hasattr(self, "tabs_widget"):
            self.tabs_widget.setTabText(0, self._ui("tab_analyse"))
            self.tabs_widget.setTabText(1, self._ui("tab_experiment"))
        if hasattr(self, "hero_title_label"):
            self.software_language_combo.blockSignals(True)
            index = self.software_language_combo.findData(self.software_language_code)
            if index >= 0:
                self.software_language_combo.setCurrentIndex(index)
            self.software_language_combo.blockSignals(False)
            self.hero_title_label.setText(self._ui("hero_title"))
            self.hero_subtitle_label.setText(self._ui("hero_subtitle"))
        if hasattr(self, "device_card_title"):
            self.device_card_title.setText(self._ui("device_title"))
            self.connect_button.setText(self._ui("connect_device"))
            self.disconnect_button.setText(self._ui("disconnect_device"))
            self.games_card_title.setText(self._ui("games_title"))
            self.launch_game_button.setText(self._ui("start_game"))
            self.play_demo_button.setText(self._ui("play_demo"))
            self.game_auto_note_label.setText(self._ui("game_auto_note"))
            self.log_card_title.setText(self._ui("session_log"))
            self.log_output.setPlaceholderText(self._ui("session_log_placeholder"))
            self.examiner_card_title.setText(self._ui("examiner_control"))
            self.planner_title_label.setText(self._ui("planner_title"))
            for field_key, label in self.examiner_field_labels.items():
                label.setText(self._ui(f"field_{field_key}"))
            self.relax_audio_checkbox.setText(self._ui("field_relax_audio"))
            for header, key in zip(
                self.planner_header_labels,
                ("planner_session", "planner_order", "planner_duration"),
            ):
                header.setText(self._ui(key))
            for stage_key, label in self.stage_name_labels.items():
                label.setText(self._stage_label(stage_key))
            for key, title in (
                ("connection", "metric_connection"),
                ("recording", "metric_recording"),
                ("battery", "metric_battery"),
                ("hr", "metric_hr"),
            ):
                self.metric_cards[key].title_label.setText(self._ui(title))
            self.rules_label.setText(
                self._ui("rules_prefix", rules=", ".join(rule.name for rule in self.architecture_agent.list_rules()))
            )
            self._update_selected_game_panels()
            self._refresh_ui()

    def _setup_window(self) -> None:
        self.setWindowTitle(self._ui("window_title"))
        self.resize(1480, 960)
        self.setMinimumSize(980, 700)
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
                font-size: 28px;
                font-weight: 800;
            }
            QLabel#HeroSubtitle {
                color: rgba(255, 248, 238, 0.84);
                font-size: 13px;
            }
            QLabel#SectionTitle, QLabel#DialogTitle {
                color: #111827;
                font-size: 16px;
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
            QLabel#ExaminerHeading {
                color: #0f172a;
                font-size: 14px;
                font-weight: 800;
            }
            QLabel#ExaminerBody {
                color: #5b6472;
                font-size: 12px;
                line-height: 1.45em;
            }
            QLabel#FieldLabel {
                color: #334155;
                font-size: 11px;
                font-weight: 800;
            }
            QLabel#PlannerHeader {
                color: #64748b;
                font-size: 11px;
                font-weight: 800;
            }
            QCheckBox {
                color: #334155;
                font-size: 12px;
                font-weight: 700;
                spacing: 8px;
            }
            QPushButton#PrimaryButton {
                background: #0f766e;
                color: white;
                border: none;
                border-radius: 16px;
                padding: 14px 18px;
                font-weight: 800;
                min-height: 48px;
            }
            QPushButton#PrimaryButton:hover {
                background: #115e59;
            }
            QPushButton#AccentButton {
                background: #f97316;
                color: white;
                border: none;
                border-radius: 16px;
                padding: 14px 18px;
                font-weight: 800;
                min-height: 48px;
            }
            QPushButton#AccentButton:hover {
                background: #ea580c;
            }
            QPushButton#SecondaryButton {
                background: #fffdf8;
                color: #1f2937;
                border: 1px solid #d9c6ae;
                border-radius: 16px;
                padding: 14px 18px;
                font-weight: 700;
                min-height: 48px;
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
                color: #1f2937;
                border: 1px solid #d9c6ae;
                border-radius: 16px;
                padding: 10px 12px;
                font-size: 12px;
                min-height: 44px;
            }
            QComboBox:hover {
                border: 1px solid #0f766e;
                background: #fffaf2;
            }
            QComboBox::drop-down {
                border: none;
                width: 28px;
            }
            QComboBox#SoftwareLanguageCombo {
                background: #d1fae5;
                color: #064e3b;
                border: 1px solid #99f6e4;
                border-radius: 18px;
                padding: 6px 14px;
                font-size: 12px;
                font-weight: 800;
                min-height: 36px;
            }
            QComboBox#SoftwareLanguageCombo:hover {
                background: #ccfbf1;
                border: 1px solid #99f6e4;
            }
            QComboBox#SoftwareLanguageCombo::drop-down {
                width: 24px;
            }
            QComboBox QAbstractItemView {
                background: #fffdf9;
                color: #1f2937;
                border: 1px solid #e3d5c3;
                border-radius: 14px;
                outline: 0;
                padding: 6px;
                selection-background-color: #dff7f2;
                selection-color: #0f172a;
            }
            QComboBox QAbstractItemView::item {
                min-height: 34px;
                padding: 8px 10px;
                margin: 2px 0;
                border-radius: 10px;
                color: #1f2937;
                background: transparent;
            }
            QComboBox QAbstractItemView::item:hover {
                background: #fff1dc;
                color: #111827;
            }
            QComboBox QAbstractItemView::item:selected {
                background: #dff7f2;
                color: #0f172a;
            }
            QLineEdit, QTextEdit {
                background: #fffdf8;
                color: #1f2937;
                border: 1px solid #d9c6ae;
                border-radius: 14px;
                padding: 10px 12px;
                font-size: 12px;
            }
            QLineEdit:focus, QTextEdit:focus, QComboBox:focus {
                border: 1px solid #0f766e;
            }
            QTabWidget::pane {
                border: 1px solid #e8dccb;
                border-radius: 24px;
                background: rgba(255, 252, 246, 0.72);
                margin-top: 10px;
            }
            QTabBar::tab {
                background: rgba(255, 249, 240, 0.82);
                color: #5b6472;
                border: 1px solid #e8dccb;
                border-bottom: none;
                border-top-left-radius: 16px;
                border-top-right-radius: 16px;
                padding: 12px 22px;
                margin-right: 6px;
                font-weight: 700;
            }
            QTabBar::tab:selected {
                background: #fffdf8;
                color: #0f172a;
            }
            QTabBar::tab:hover:!selected {
                background: #fff7eb;
                color: #1f2937;
            }
            """
        )

    def _build_ui(self) -> None:
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.setCentralWidget(scroll_area)

        root = QWidget()
        root.setObjectName("Root")
        scroll_area.setWidget(root)

        page = QVBoxLayout(root)
        page.setContentsMargins(20, 20, 20, 20)
        page.setSpacing(18)
        page.addWidget(self._build_header())
        page.addWidget(self._build_tabs(), stretch=1)

    def _build_tabs(self) -> QTabWidget:
        self.tabs_widget = QTabWidget()
        self.tabs_widget.addTab(self._build_analyse_tab(), self._ui("tab_analyse"))
        self.tabs_widget.addTab(self._build_experiment_tab(), self._ui("tab_experiment"))
        return self.tabs_widget

    def _build_analyse_tab(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.analyse_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.analyse_splitter.setChildrenCollapsible(False)
        self.analyse_splitter.addWidget(self._build_signal_area())
        self.analyse_splitter.addWidget(self._build_analyse_sidebar())
        self.analyse_splitter.setStretchFactor(0, 5)
        self.analyse_splitter.setStretchFactor(1, 2)
        self.analyse_splitter.splitterMoved.connect(lambda _pos, _index: self._relayout_signal_area())
        layout.addWidget(self.analyse_splitter)
        QTimer.singleShot(0, lambda: self.analyse_splitter.setSizes([980, 420]))
        return container

    def _build_experiment_tab(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content = QWidget()
        content.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        layout = QVBoxLayout(content)
        layout.setContentsMargins(14, 16, 14, 14)
        layout.setSpacing(16)
        game_card = self._build_game_card()
        game_card.setMinimumWidth(520)
        game_card.setMaximumWidth(760)
        examiner_card = self._build_examiner_card()
        examiner_card.setMinimumWidth(360)
        examiner_card.setMaximumWidth(520)
        cards_row = QHBoxLayout()
        cards_row.setContentsMargins(0, 0, 0, 0)
        cards_row.setSpacing(18)
        cards_row.addStretch(1)
        cards_row.addWidget(game_card, 3)
        cards_row.addWidget(examiner_card, 2)
        cards_row.addStretch(1)
        layout.addLayout(cards_row)
        layout.addStretch(1)
        scroll.setWidget(content)
        self._update_selected_game_panels()
        return scroll

    def _centered_row(self, widget: QWidget) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(0)
        row.addStretch(1)
        row.addWidget(widget)
        row.addStretch(1)
        return row

    def _build_header(self) -> QFrame:
        card = QFrame()
        card.setObjectName("HeroCard")
        layout = QHBoxLayout(card)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(22)

        text_column = QVBoxLayout()
        self.hero_title_label = QLabel(self._ui("hero_title"))
        self.hero_title_label.setObjectName("HeroTitle")
        self.hero_subtitle_label = QLabel(self._ui("hero_subtitle"))
        self.hero_subtitle_label.setObjectName("HeroSubtitle")
        self.hero_subtitle_label.setWordWrap(True)
        text_column.addWidget(self.hero_title_label)
        text_column.addWidget(self.hero_subtitle_label)

        badge_column = QVBoxLayout()
        badge_column.setSpacing(8)
        badge_row = QHBoxLayout()
        badge_row.setSpacing(10)
        self.session_badge = QLabel(self._ui("idle"))
        self.recording_badge = QLabel(self._ui("recording_off"))
        self._set_badge_style(self.session_badge, active=False, accent="teal")
        self._set_badge_style(self.recording_badge, active=False, accent="orange")
        badge_row.addWidget(self.session_badge)
        badge_row.addWidget(self.recording_badge)
        badge_column.addLayout(badge_row)
        self.software_language_combo = QComboBox()
        self.software_language_combo.setObjectName("SoftwareLanguageCombo")
        self.software_language_combo.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.software_language_combo.setFixedWidth(170)
        for language_code, language_bundle in self.software_languages.items():
            display_name, _native_name = language_bundle
            self.software_language_combo.addItem(display_name, language_code)
        badge_column.addWidget(self.software_language_combo, alignment=Qt.AlignmentFlag.AlignRight)
        badge_column.addStretch(1)

        layout.addLayout(text_column, stretch=1)
        layout.addLayout(badge_column)
        return card

    def _build_signal_area(self) -> QWidget:
        container = QWidget()
        self.signal_area_widget = container
        container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        self.metric_grid = QGridLayout()
        self.metric_grid.setHorizontalSpacing(10)
        self.metric_grid.setVerticalSpacing(10)
        self.metric_cards["connection"] = MetricCard(self._ui("metric_connection"), "#0f766e")
        self.metric_cards["recording"] = MetricCard(self._ui("metric_recording"), "#f97316")
        self.metric_cards["battery"] = MetricCard(self._ui("metric_battery"), "#dc2626")
        self.metric_cards["hr"] = MetricCard(self._ui("metric_hr"), "#1d4ed8")
        self.metric_card_widgets = [
            self.metric_cards["connection"],
            self.metric_cards["recording"],
            self.metric_cards["battery"],
            self.metric_cards["hr"],
        ]
        layout.addLayout(self.metric_grid)

        self.plot_grid = QGridLayout()
        self.plot_grid.setHorizontalSpacing(12)
        self.plot_grid.setVerticalSpacing(12)
        for index, channel in enumerate(self.config.eeg_channels):
            card = PlotCard(channel.name, self.config.eeg_colors[index], self.config.eeg_plot_range_uv)
            self.plot_cards.append(card)
            self.eeg_plot_widgets.append(card)
        ppg_card = PlotCard("PPG (RED - LUX, bandpassed)", "#7c3aed", self.config.ppg_plot_range)
        self.plot_cards.append(ppg_card)
        self.ppg_plot_card = ppg_card
        layout.addLayout(self.plot_grid, stretch=1)
        self._relayout_signal_area()
        return container

    def _build_analyse_sidebar(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        sidebar = QWidget()
        scroll.setWidget(sidebar)
        sidebar.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        layout.addWidget(self._build_device_card())
        layout.addWidget(self._build_log_card(), stretch=1)
        layout.addStretch(1)
        return scroll

    def _build_device_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("SidebarCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(10)

        self.device_card_title = QLabel(self._ui("device_title"))
        self.device_card_title.setObjectName("SectionTitle")
        layout.addWidget(self.device_card_title)

        self.connect_button = QPushButton(self._ui("connect_device"))
        self.connect_button.setObjectName("PrimaryButton")
        self.connect_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.disconnect_button = QPushButton(self._ui("disconnect_device"))
        self.disconnect_button.setObjectName("SecondaryButton")
        self.disconnect_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout.addWidget(self.connect_button)
        layout.addWidget(self.disconnect_button)

        self.record_button = QPushButton(self._ui("record_data"))
        self.record_button.setObjectName("AccentButton")
        self.record_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout.addWidget(self.record_button)

        self.device_label = QLabel(self._ui("selected_device_none"))
        self.device_label.setObjectName("SupportText")
        self.device_label.setWordWrap(True)
        layout.addWidget(self.device_label)

        self.eeg_status_label = QLabel()
        self.ppg_status_label = QLabel()
        self._set_stream_label(self.eeg_status_label, "EEG", False)
        self._set_stream_label(self.ppg_status_label, "PPG", False)
        layout.addWidget(self.eeg_status_label)
        layout.addWidget(self.ppg_status_label)

        self.last_save_label = QLabel(self._ui("last_save_prefix") + self._ui("last_save_none"))
        self.last_save_label.setObjectName("SupportText")
        self.last_save_label.setWordWrap(True)
        layout.addWidget(self.last_save_label)

        rules = ", ".join(rule.name for rule in self.architecture_agent.list_rules())
        self.rules_label = QLabel(self._ui("rules_prefix", rules=rules))
        self.rules_label.setObjectName("SupportText")
        self.rules_label.setWordWrap(True)
        layout.addWidget(self.rules_label)
        return card

    def _build_game_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("SidebarCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(26, 24, 26, 24)
        layout.setSpacing(14)

        self.games_card_title = QLabel(self._ui("games_title"))
        self.games_card_title.setObjectName("SectionTitle")
        layout.addWidget(self.games_card_title)

        self.game_combo = QComboBox()
        self.game_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.game_combo.setMaximumWidth(620)
        for game in self.game_registry.list_games():
            self.game_combo.addItem(game.title, game.game_id)
        layout.addLayout(self._centered_row(self.game_combo))

        self.game_language_combo = QComboBox()
        self.game_language_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.game_language_combo.setMaximumWidth(620)
        layout.addLayout(self._centered_row(self.game_language_combo))

        self.game_description_label = QLabel()
        self.game_description_label.setObjectName("SupportText")
        self.game_description_label.setWordWrap(True)
        self.game_description_label.setMaximumWidth(760)
        layout.addLayout(self._centered_row(self.game_description_label))

        self.launch_game_button = QPushButton(self._ui("start_game"))
        self.launch_game_button.setObjectName("PrimaryButton")
        self.launch_game_button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.launch_game_button.setFixedSize(170, 42)
        layout.addLayout(self._centered_row(self.launch_game_button))

        self.play_demo_button = QPushButton(self._ui("play_demo"))
        self.play_demo_button.setObjectName("SecondaryButton")
        self.play_demo_button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.play_demo_button.setFixedSize(170, 42)
        layout.addLayout(self._centered_row(self.play_demo_button))
        layout.addSpacing(10)

        self.game_auto_note_label = QLabel(self._ui("game_auto_note"))
        self.game_auto_note_label.setObjectName("SupportText")
        self.game_auto_note_label.setWordWrap(True)
        self.game_auto_note_label.setMaximumWidth(760)
        layout.addLayout(self._centered_row(self.game_auto_note_label))

        self._update_selected_game_panels()
        return card

    def _clear_layout(self, grid: QGridLayout) -> None:
        while grid.count():
            item = grid.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)

    def _relayout_signal_area(self) -> None:
        signal_width = self.signal_area_widget.width() if hasattr(self, "signal_area_widget") else self.width()
        metric_width = max(1, signal_width)
        if metric_width >= 1300:
            metric_columns = 4
        elif metric_width >= 900:
            metric_columns = 2
        else:
            metric_columns = 1

        self._clear_layout(self.metric_grid)
        for index, card in enumerate(self.metric_card_widgets):
            row = index // metric_columns
            column = index % metric_columns
            self.metric_grid.addWidget(card, row, column)

        plot_width = max(1, signal_width)
        plot_columns = 2 if plot_width >= 900 else 1
        self._clear_layout(self.plot_grid)
        for index, card in enumerate(self.eeg_plot_widgets):
            row = index // plot_columns
            column = index % plot_columns
            self.plot_grid.addWidget(card, row, column)

        if self.ppg_plot_card is not None:
            ppg_row = (len(self.eeg_plot_widgets) + plot_columns - 1) // plot_columns
            self.plot_grid.addWidget(self.ppg_plot_card, ppg_row, 0, 1, plot_columns)

    def _build_log_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("SidebarCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(26, 24, 26, 24)
        layout.setSpacing(12)

        self.log_card_title = QLabel(self._ui("session_log"))
        self.log_card_title.setObjectName("SectionTitle")
        self.log_output = QPlainTextEdit()
        self.log_output.setObjectName("LogOutput")
        self.log_output.setReadOnly(True)
        self.log_output.setPlaceholderText(self._ui("session_log_placeholder"))
        layout.addWidget(self.log_card_title)
        layout.addWidget(self.log_output)
        return card

    def _build_examiner_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("SidebarCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(26, 24, 26, 24)
        layout.setSpacing(14)

        self.examiner_card_title = QLabel(self._ui("examiner_control"))
        self.examiner_card_title.setObjectName("SectionTitle")
        layout.addWidget(self.examiner_card_title)

        self.examiner_subtitle_label = QLabel()
        self.examiner_subtitle_label.setObjectName("ExaminerBody")
        self.examiner_subtitle_label.setWordWrap(True)
        layout.addWidget(self.examiner_subtitle_label)

        form_grid = QGridLayout()
        form_grid.setHorizontalSpacing(10)
        form_grid.setVerticalSpacing(10)

        self.examiner_name_input = QLineEdit()
        self.examiner_id_input = QLineEdit()
        self.examiner_age_input = QLineEdit()
        self.examiner_n_value_input = QLineEdit("3")
        self.examiner_n_value_input.setMaximumWidth(120)
        self.examiner_note_input = QTextEdit()
        self.examiner_note_input.setFixedHeight(88)

        self.examiner_field_labels: dict[str, QLabel] = {}
        form_fields = [
            ("name", self.examiner_name_input),
            ("id", self.examiner_id_input),
            ("age", self.examiner_age_input),
            ("n_value", self.examiner_n_value_input),
            ("note", self.examiner_note_input),
        ]
        for row, (field_key, widget) in enumerate(form_fields):
            label = QLabel(self._ui(f"field_{field_key}"))
            label.setObjectName("FieldLabel")
            self.examiner_field_labels[field_key] = label
            form_grid.addWidget(label, row, 0)
            form_grid.addWidget(widget, row, 1)
        form_grid.setColumnStretch(1, 1)
        layout.addLayout(form_grid)

        self.relax_audio_checkbox = QCheckBox(self._ui("field_relax_audio"))
        layout.addWidget(self.relax_audio_checkbox)

        self.planner_title_label = QLabel(self._ui("planner_title"))
        self.planner_title_label.setObjectName("ExaminerHeading")
        layout.addWidget(self.planner_title_label)

        planner_grid = QGridLayout()
        planner_grid.setHorizontalSpacing(10)
        planner_grid.setVerticalSpacing(10)
        self.planner_header_labels: list[QLabel] = []
        planner_headers = ["planner_session", "planner_order", "planner_duration"]
        for column, header_key in enumerate(planner_headers):
            header = QLabel(self._ui(header_key))
            header.setObjectName("PlannerHeader")
            self.planner_header_labels.append(header)
            planner_grid.addWidget(header, 0, column)

        self.stage_order_inputs: dict[str, QLineEdit] = {}
        self.stage_duration_inputs: dict[str, QLineEdit] = {}
        self.stage_name_labels: dict[str, QLabel] = {}
        default_stage_values = [
            ("relax", "1", "2"),
            ("break", "2", "2"),
            ("game", "3", "1"),
        ]
        for row, (stage_key, order_value, duration_value) in enumerate(default_stage_values, start=1):
            stage_label = QLabel(self._stage_label(stage_key))
            self.stage_name_labels[stage_key] = stage_label
            planner_grid.addWidget(stage_label, row, 0)
            order_input = QLineEdit(order_value)
            duration_input = QLineEdit(duration_value)
            order_input.setMaximumWidth(70)
            duration_input.setMaximumWidth(120)
            self.stage_order_inputs[stage_key] = order_input
            self.stage_duration_inputs[stage_key] = duration_input
            planner_grid.addWidget(order_input, row, 1)
            planner_grid.addWidget(duration_input, row, 2)
        planner_grid.setColumnStretch(2, 1)
        layout.addLayout(planner_grid)

        self.examiner_help_label = QLabel()
        self.examiner_help_label.setObjectName("ExaminerBody")
        self.examiner_help_label.setWordWrap(True)
        layout.addWidget(self.examiner_help_label)

        layout.addStretch(1)
        return card

    def _connect_events(self) -> None:
        self.connect_button.clicked.connect(self._open_device_dialog)
        self.disconnect_button.clicked.connect(self._disconnect_async)
        self.record_button.clicked.connect(self._toggle_recording)
        self.launch_game_button.clicked.connect(self._launch_selected_game_async)
        self.play_demo_button.clicked.connect(self._launch_demo_async)
        self.game_combo.currentIndexChanged.connect(self._update_selected_game_panels)
        self.game_language_combo.currentIndexChanged.connect(self._update_selected_game_panels)
        self.software_language_combo.currentIndexChanged.connect(self._handle_software_language_changed)
        self.timer.timeout.connect(self._refresh_ui)

    def _handle_software_language_changed(self) -> None:
        language_code = self.software_language_combo.currentData() or "en"
        self.software_language_code = language_code
        self._apply_software_language()

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
                self._ui("connect_device_title"),
                self._ui("connect_device_failed", error=error),
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
            QMessageBox.warning(
                self,
                self._ui("disconnect_device_title"),
                self._ui("disconnect_device_failed", error=error),
            )
            return
        if saved_files is None:
            self._append_log("Device disconnected.")

    def _toggle_recording(self) -> None:
        status = self.controller.status()
        if not status.running:
            QMessageBox.information(
                self,
                self._ui("record_data_title"),
                self._ui("no_device_recording"),
            )
            return

        if status.recording:
            saved_files = self.controller.stop_recording(save=True)
            if saved_files is not None:
                self._append_log("Manual recording session saved.")
        else:
            self.controller.set_save_context(**self._current_save_context())
            self.controller.start_recording()

    def _launch_selected_game_async(self) -> None:
        game_id = self.game_combo.currentData()
        if game_id is None:
            return
        language_code = self.game_language_combo.currentData() or "en"
        examiner_setup = self._collect_examiner_setup()
        if examiner_setup is None:
            return
        self.controller.set_save_context(**self._save_context_from_examiner_setup(examiner_setup))

        status = self.controller.status()
        self.pending_game_auto_record = False
        if not status.running:
            QMessageBox.information(
                self,
                self._ui("start_game_title"),
                self._ui("start_game_no_device"),
            )

        self.launch_game_button.setEnabled(False)
        self.play_demo_button.setEnabled(False)
        threading.Thread(
            target=self._launch_game_worker,
            args=(game_id, language_code, examiner_setup, False, None),
            daemon=True,
        ).start()

    def _launch_demo_async(self) -> None:
        game_id = self.game_combo.currentData()
        if game_id is None:
            return
        language_code = self.game_language_combo.currentData() or "en"
        demo_n_value = self._collect_demo_n_value()
        if demo_n_value is None:
            return

        self.pending_game_auto_record = False
        self.launch_game_button.setEnabled(False)
        self.play_demo_button.setEnabled(False)
        threading.Thread(
            target=self._launch_game_worker,
            args=(game_id, language_code, None, True, demo_n_value),
            daemon=True,
        ).start()

    def _launch_game_worker(
        self,
        game_id: str,
        language_code: str,
        examiner_setup: dict[str, object] | None,
        demo_mode: bool,
        demo_n_value: int | None,
    ) -> None:
        try:
            process = self.game_registry.launch(
                game_id,
                language_code=language_code,
                examiner_setup=examiner_setup,
                demo_mode=demo_mode,
                demo_n_value=demo_n_value,
            )
            self.game_launch_completed.emit({"game_id": game_id, "demo_mode": demo_mode}, process)
        except Exception as exc:
            self.game_launch_completed.emit({"game_id": game_id, "demo_mode": demo_mode}, str(exc))

    def _finish_game_launch(self, launch_info, result) -> None:
        game_id = launch_info["game_id"]
        demo_mode = bool(launch_info.get("demo_mode"))
        self.launch_game_button.setEnabled(True)
        self.play_demo_button.setEnabled(True)
        if isinstance(result, str):
            if self.pending_game_auto_record and self.controller.status().recording:
                self.controller.stop_recording(save=True)
            self._append_log(f"Could not launch game: {result}")
            QMessageBox.warning(self, self._ui("start_game_title"), f"{result}")
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
        if demo_mode:
            self._append_log(f"Launched {self.game_registry.get(game_id).title} demo in a separate game window.")
        else:
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
        self.session_badge.setText(self._ui("connected") if status.running else self._ui("disconnected"))
        self._set_badge_style(self.recording_badge, active=status.recording, accent="orange")
        self.recording_badge.setText(self._ui("recording_on") if status.recording else self._ui("recording_off"))

        self.connect_button.setEnabled(not self.connection_busy)
        self.disconnect_button.setEnabled((status.running or self.device_manager.is_connected()) and not self.connection_busy)
        self.record_button.setEnabled(not self.connection_busy)
        self.record_button.setText(self._ui("stop_recording") if status.recording else self._ui("record_data"))

        if current_device is None:
            self.device_label.setText(self._ui("selected_device_none"))
        else:
            prefix = self._ui("selected_device_none").split(":")[0]
            self.device_label.setText(f"{prefix}: {current_device.display_name}")
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
        self.metric_cards["connection"].set_value(
            self._ui("metric_live") if status.running else self._ui("metric_offline"),
            self._ui("metric_stream_state"),
        )
        self.metric_cards["recording"].set_value(
            "REC" if status.recording else self._ui("metric_standby"),
            self._ui("metric_capture_mode"),
        )
        self.metric_cards["battery"].set_value(
            f"{battery:.0f}%" if battery is not None else "--%",
            self._ui("metric_device_battery") if battery is not None else self._ui("metric_battery_unavailable"),
        )
        self.metric_cards["hr"].set_value(
            f"{bpm:.1f} bpm" if bpm is not None else "-- bpm",
            self._ui("metric_latest_estimate"),
        )
        self.last_save_label.setText(self._ui("last_save_prefix") + self.last_saved_text)

        self._prune_finished_games()

    def _update_selected_game_panels(self) -> None:
        game_id = self.game_combo.currentData()
        if game_id is None:
            self.game_description_label.setText(self._ui("no_game_selected"))
            if hasattr(self, "examiner_subtitle_label"):
                self.examiner_subtitle_label.setText(self._ui("examiner_empty"))
                self.examiner_help_label.setText("")
            return
        game = self.game_registry.get(game_id)
        self.game_language_combo.blockSignals(True)
        current_language = self.game_language_combo.currentData()
        self.game_language_combo.clear()
        for language_code in game.supported_languages:
            self.game_language_combo.addItem(
                self.game_languages.get(language_code, language_code),
                language_code,
            )
        if current_language in game.supported_languages:
            self.game_language_combo.setCurrentIndex(game.supported_languages.index(current_language))
        self.game_language_combo.blockSignals(False)
        details = [
            self._ui("game_language_prefix", languages=", ".join(
                self.game_languages.get(language_code, language_code)
                for language_code in game.supported_languages
            ))
        ]
        self.game_description_label.setText(
            "\n\n".join(details)
        )
        self._update_examiner_preview(game)

    def _update_examiner_preview(self, game) -> None:
        if not hasattr(self, "examiner_subtitle_label"):
            return
        preview_map = game.examiner_preview or {}
        preview = preview_map.get(self.software_language_code) or preview_map.get("en")
        if preview is None:
            preview = ExaminerPreview(
                heading=self._ui("examiner_control"),
                subtitle=self._ui("examiner_default_subtitle"),
            )

        self.examiner_subtitle_label.setText(preview.subtitle)
        self.examiner_help_label.setText(
            self._ui(
                "examiner_language",
                language=self.software_languages.get(self.software_language_code, ("English", "English"))[1],
            )
            + "\n\n"
            + self._ui("planner_help")
        )

    def _collect_demo_n_value(self) -> int | None:
        n_value_text = self.examiner_n_value_input.text().strip()
        if not n_value_text:
            QMessageBox.warning(self, self._ui("examiner_control"), self._ui("n_value_required"))
            return None
        try:
            n_value = int(n_value_text)
        except ValueError:
            QMessageBox.warning(self, self._ui("examiner_control"), self._ui("n_value_integer"))
            return None
        if n_value < 1:
            QMessageBox.warning(self, self._ui("examiner_control"), self._ui("n_value_positive"))
            return None
        return n_value

    def _collect_examiner_setup(self) -> dict[str, object] | None:
        participant_name = self.examiner_name_input.text().strip()
        participant_id = self.examiner_id_input.text().strip()
        age = self.examiner_age_input.text().strip()
        n_value_text = self.examiner_n_value_input.text().strip()
        relax_audio_enabled = self.relax_audio_checkbox.isChecked()
        note = self.examiner_note_input.toPlainText().strip()

        if not participant_name:
            QMessageBox.warning(self, self._ui("examiner_control"), self._ui("name_required"))
            return None
        if not participant_id:
            QMessageBox.warning(self, self._ui("examiner_control"), self._ui("id_required"))
            return None
        if not age:
            QMessageBox.warning(self, self._ui("examiner_control"), self._ui("age_required"))
            return None
        if not n_value_text:
            QMessageBox.warning(self, self._ui("examiner_control"), self._ui("n_value_required"))
            return None
        try:
            n_value = int(n_value_text)
        except ValueError:
            QMessageBox.warning(self, self._ui("examiner_control"), self._ui("n_value_integer"))
            return None
        if n_value < 1:
            QMessageBox.warning(self, self._ui("examiner_control"), self._ui("n_value_positive"))
            return None

        stage_plan: list[dict[str, object]] = []
        orders: list[int] = []
        for stage_key in ("relax", "break", "game"):
            order_text = self.stage_order_inputs[stage_key].text().strip()
            duration_text = self.stage_duration_inputs[stage_key].text().strip()
            try:
                order = int(order_text)
            except ValueError:
                QMessageBox.warning(self, self._ui("examiner_control"), self._ui("order_whole_number", stage=self._stage_label(stage_key)))
                return None
            try:
                duration = float(duration_text)
            except ValueError:
                QMessageBox.warning(self, self._ui("examiner_control"), self._ui("duration_number", stage=self._stage_label(stage_key)))
                return None
            if order not in (1, 2, 3):
                QMessageBox.warning(self, self._ui("examiner_control"), self._ui("order_range", stage=self._stage_label(stage_key)))
                return None
            if duration < 0:
                QMessageBox.warning(self, self._ui("examiner_control"), self._ui("duration_negative", stage=self._stage_label(stage_key)))
                return None
            orders.append(order)
            stage_plan.append({"kind": stage_key, "order": order, "duration_minutes": duration})

        if sorted(orders) != [1, 2, 3]:
            QMessageBox.warning(self, self._ui("examiner_control"), self._ui("order_unique"))
            return None
        game_stage = next(stage for stage in stage_plan if stage["kind"] == "game")
        if float(game_stage["duration_minutes"]) <= 0:
            QMessageBox.warning(self, self._ui("examiner_control"), self._ui("game_duration_positive"))
            return None

        return {
            "participant_name": participant_name,
            "participant_id": participant_id,
            "age": age,
            "n_value": n_value,
            "relax_audio_enabled": relax_audio_enabled,
            "note": note,
            "session_stages": stage_plan,
        }

    def _append_log(self, message: str) -> None:
        stamp = datetime.now().strftime("%H:%M:%S")
        self.log_output.appendPlainText(f"[{stamp}] {message}")
        if message.startswith("Saved to "):
            self.last_saved_text = message.removeprefix("Saved to ")

    def _current_save_context(self) -> dict[str, str]:
        return self._save_context_from_examiner_setup(
            {
                "participant_id": self.examiner_id_input.text().strip(),
                "session_stages": [
                    {
                        "kind": stage_key,
                        "order": self.stage_order_inputs[stage_key].text().strip() or "0",
                    }
                    for stage_key in ("relax", "break", "game")
                ],
            }
        )

    @staticmethod
    def _save_context_from_examiner_setup(examiner_setup: dict[str, object]) -> dict[str, str]:
        participant_id = str(examiner_setup.get("participant_id", "")).strip() or "unknown"
        session_stages = examiner_setup.get("session_stages", [])
        session_label = ModernMuseWindow._session_label_from_stages(session_stages)
        return {"user_id": participant_id, "session_label": session_label}

    @staticmethod
    def _session_label_from_stages(session_stages: object) -> str:
        mapping = {"relax": "A", "game": "B", "break": "C"}
        ordered: list[tuple[int, str]] = []
        for stage in session_stages if isinstance(session_stages, list) else []:
            if not isinstance(stage, dict):
                continue
            kind = str(stage.get("kind", "")).strip().lower()
            try:
                order = int(stage.get("order", 0))
            except (TypeError, ValueError):
                continue
            if kind in mapping and order > 0:
                ordered.append((order, mapping[kind]))
        ordered.sort(key=lambda item: item[0])
        return "".join(label for _, label in ordered) or "ABC"

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
        label.setText(
            self._ui("stream_connected", name=name) if connected else self._ui("stream_waiting", name=name)
        )
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

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._relayout_signal_area()
