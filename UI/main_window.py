from __future__ import annotations

import json
import shutil
import subprocess
import threading
import time
from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import QTimer, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QPalette
from PyQt6.QtWidgets import (
    QBoxLayout,
    QCheckBox,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QPlainTextEdit,
    QApplication,
    QScrollArea,
    QSlider,
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
from UI.widgets import MetricCard, PlotCard, SlideSwitch


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
            "examiner_default_subtitle": "Configure participant details and arrange Relax (A), Break (B), and Game (C) before launching the game.",
            "field_name": "Name",
            "field_id": "ID",
            "field_id_hint": "Write only the ID number. Prefix P is added automatically to saved files.",
            "field_device_id": "DeviceID",
            "field_age": "Age",
            "field_n_value": "N Value",
            "field_note": "Note",
            "field_relax_audio": "Play music during Relax",
            "field_music_track": "Music track",
            "music_binaural_sound": "Binaural sound",
            "music_rain_sound": "Rain sound",
            "music_switch_on": "On",
            "music_switch_off": "Off",
            "field_announcement_volume": "Announcement volume",
            "planner_title": "Session Planner",
            "planner_session": "Session",
            "planner_order": "Order",
            "planner_duration": "Duration (minutes)",
            "stage_relax": "Relax",
            "stage_break": "Break",
            "stage_game": "Game",
            "planner_help": "Arrange Relax (A), Break (B), and Game (C) freely using orders 1, 2, and 3 exactly once. You can set a stage duration to 0 to skip it, but Game must be greater than 0.",
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
            "device_id_required": "DeviceID is required.",
            "age_required": "Age is required.",
            "n_value_required": "N value is required.",
            "n_value_integer": "N value must be a whole number.",
            "n_value_positive": "N value must be at least 1.",
            "order_whole_number": "{stage} order must be a whole number.",
            "duration_number": "{stage} duration must be a number.",
            "order_range": "{stage} order must be 1, 2, or 3.",
            "duration_negative": "{stage} duration can not be negative.",
            "order_unique": "Relax, Break, and Game must use orders 1, 2, and 3 exactly once.",
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
            "field_id_hint": "Write only the ID number. Prefix P is added automatically to saved files.",
            "field_age": "Alter",
            "field_n_value": "N-Wert",
            "field_note": "Notiz",
            "field_relax_audio": "Musik waehrend Entspannung abspielen",
            "field_announcement_volume": "Lautstaerke der Ansage",
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
            "field_id_hint": "Write only the ID number. Prefix P is added automatically to saved files.",
            "field_age": "Tuổi",
            "field_n_value": "Giá trị N",
            "field_note": "Ghi chú",
            "field_relax_audio": "Phát nhạc trong lúc Thư giãn",
            "field_announcement_volume": "Âm lượng thông báo",
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
        "zh": {
            "window_title": "EEG 分析",
            "tab_analyse": "分析",
            "tab_experiment": "实验设置",
            "hero_title": "EEG 分析",
            "hero_subtitle": "由 CuongFX 设计",
            "idle": "空闲",
            "disconnected": "未连接",
            "connected": "设备已连接",
            "recording_off": "未录制",
            "recording_on": "录制中",
            "metric_connection": "连接状态",
            "metric_recording": "录制状态",
            "metric_battery": "电量",
            "metric_hr": "心率",
            "metric_stream_state": "流状态",
            "metric_capture_mode": "采集模式",
            "metric_device_battery": "设备电量",
            "metric_battery_unavailable": "无电量数据",
            "metric_latest_estimate": "最新估计",
            "metric_live": "在线",
            "metric_offline": "离线",
            "metric_standby": "待机",
            "device_title": "设备 + 录制",
            "connect_device": "连接设备",
            "disconnect_device": "断开设备",
            "record_data": "开始录制",
            "stop_recording": "停止录制",
            "selected_device_none": "已选设备：无",
            "last_save_none": "尚未保存录制文件",
            "last_save_prefix": "最近保存：",
            "rules_prefix": "架构规则：{rules}",
            "games_title": "游戏",
            "game_language_prefix": "游戏语言：{languages}",
            "start_game": "开始游戏",
            "play_demo": "演示模式",
            "game_auto_note": "启动游戏时，如设备已连接且未在录制，将自动开始录制。",
            "session_log": "会话日志",
            "session_log_placeholder": "连接事件、录制状态和游戏启动信息会显示在这里。",
            "examiner_control": "监考控制",
            "examiner_empty": "暂无监考控制内容。",
            "examiner_default_subtitle": "启动游戏前请先配置参与者信息和会话细节。",
            "field_name": "姓名",
            "field_id": "ID",
            "field_id_hint": "Write only the ID number. Prefix P is added automatically to saved files.",
            "field_age": "年龄",
            "field_n_value": "N 值",
            "field_note": "备注",
            "field_relax_audio": "放松阶段播放音乐",
            "field_announcement_volume": "提示音音量",
            "planner_title": "会话计划",
            "planner_session": "阶段",
            "planner_order": "顺序",
            "planner_duration": "时长（分钟）",
            "stage_relax": "放松",
            "stage_break": "休息",
            "stage_game": "游戏",
            "planner_help": "顺序 1、2、3 必须且只能各使用一次。阶段时长可设为 0 表示跳过，但游戏阶段必须大于 0。",
            "examiner_language": "语言：{language}",
            "stream_connected": "{name} 流已连接",
            "stream_waiting": "{name} 流等待中",
            "no_game_selected": "未选择游戏。",
            "no_device_recording": "请先连接设备。只有 Muse 流连接后才能录制。",
            "record_data_title": "录制数据",
            "start_game_title": "开始游戏",
            "start_game_no_device": "游戏将打开，但由于未连接设备，EEG/PPG 录制指令将被忽略。",
            "connect_device_title": "连接设备",
            "disconnect_device_title": "断开设备",
            "connect_device_failed": "无法连接所选设备。\n\n{error}",
            "disconnect_device_failed": "无法断开设备连接。\n\n{error}",
            "name_required": "姓名为必填项。",
            "id_required": "ID 为必填项。",
            "age_required": "年龄为必填项。",
            "n_value_required": "N 值为必填项。",
            "n_value_integer": "N 值必须是整数。",
            "n_value_positive": "N 值必须大于或等于 1。",
            "order_whole_number": "{stage} 的顺序必须是整数。",
            "duration_number": "{stage} 的时长必须是数字。",
            "order_range": "{stage} 的顺序必须是 1、2 或 3。",
            "duration_negative": "{stage} 的时长不能为负数。",
            "order_unique": "放松、休息和游戏必须分别使用 1、2、3，且各一次。",
            "game_duration_positive": "游戏阶段时长必须大于 0。",
        },
        "ar": {
            "window_title": "تحليل EEG",
            "tab_analyse": "التحليل",
            "tab_experiment": "إعداد التجربة",
            "hero_title": "تحليل EEG",
            "hero_subtitle": "تصميم CuongFX",
            "idle": "خامل",
            "disconnected": "غير متصل",
            "connected": "الجهاز متصل",
            "recording_off": "لا يوجد تسجيل",
            "recording_on": "جارٍ التسجيل",
            "metric_connection": "الاتصال",
            "metric_recording": "التسجيل",
            "metric_battery": "البطارية",
            "metric_hr": "معدل القلب",
            "metric_stream_state": "حالة البث",
            "metric_capture_mode": "وضع الالتقاط",
            "metric_device_battery": "بطارية الجهاز",
            "metric_battery_unavailable": "لا تتوفر بيانات البطارية",
            "metric_latest_estimate": "أحدث تقدير",
            "metric_live": "مباشر",
            "metric_offline": "غير متصل",
            "metric_standby": "استعداد",
            "device_title": "الجهاز + التسجيل",
            "connect_device": "اتصال بالجهاز",
            "disconnect_device": "فصل الجهاز",
            "record_data": "تسجيل البيانات",
            "stop_recording": "إيقاف التسجيل",
            "selected_device_none": "الجهاز المحدد: لا يوجد",
            "last_save_none": "لم يتم حفظ أي تسجيل بعد",
            "last_save_prefix": "آخر حفظ: ",
            "rules_prefix": "قواعد المعمارية: {rules}",
            "games_title": "الألعاب",
            "game_language_prefix": "لغة اللعبة: {languages}",
            "start_game": "بدء اللعبة",
            "play_demo": "تشغيل العرض التجريبي",
            "game_auto_note": "بدء اللعبة سيبدأ التسجيل تلقائياً إذا كان الجهاز متصلاً ولم يكن التسجيل نشطاً.",
            "session_log": "سجل الجلسة",
            "session_log_placeholder": "ستظهر هنا أحداث الاتصال وحالة التسجيل وتشغيل اللعبة.",
            "examiner_control": "تحكم المُشرف",
            "examiner_empty": "لا يوجد تحكم مُشرف متاح.",
            "examiner_default_subtitle": "قم بإعداد بيانات المشارك وتفاصيل الجلسة قبل تشغيل اللعبة.",
            "field_name": "الاسم",
            "field_id": "المعرف",
            "field_id_hint": "Write only the ID number. Prefix P is added automatically to saved files.",
            "field_age": "العمر",
            "field_n_value": "قيمة N",
            "field_note": "ملاحظة",
            "field_relax_audio": "تشغيل الموسيقى أثناء الاسترخاء",
            "field_announcement_volume": "مستوى صوت التنبيه",
            "planner_title": "مخطط الجلسة",
            "planner_session": "الجلسة",
            "planner_order": "الترتيب",
            "planner_duration": "المدة (دقائق)",
            "stage_relax": "استرخاء",
            "stage_break": "استراحة",
            "stage_game": "اللعبة",
            "planner_help": "استخدم الترتيب 1 و2 و3 مرة واحدة فقط لكل منها. يمكن ضبط مدة أي مرحلة على 0 لتخطيها، لكن مدة اللعبة يجب أن تكون أكبر من 0.",
            "examiner_language": "اللغة: {language}",
            "stream_connected": "بث {name} متصل",
            "stream_waiting": "بث {name} بانتظار الاتصال",
            "no_game_selected": "لم يتم اختيار لعبة.",
            "no_device_recording": "يرجى توصيل الجهاز أولاً. يعمل التسجيل فقط بعد اتصال بث Muse.",
            "record_data_title": "تسجيل البيانات",
            "start_game_title": "بدء اللعبة",
            "start_game_no_device": "سيتم فتح اللعبة، لكن سيتم تجاهل أوامر تسجيل EEG/PPG لعدم وجود جهاز متصل.",
            "connect_device_title": "اتصال بالجهاز",
            "disconnect_device_title": "فصل الجهاز",
            "connect_device_failed": "تعذر الاتصال بالجهاز المحدد.\n\n{error}",
            "disconnect_device_failed": "تعذر فصل الجهاز.\n\n{error}",
            "name_required": "الاسم مطلوب.",
            "id_required": "المعرف مطلوب.",
            "age_required": "العمر مطلوب.",
            "n_value_required": "قيمة N مطلوبة.",
            "n_value_integer": "يجب أن تكون قيمة N رقماً صحيحاً.",
            "n_value_positive": "يجب أن تكون قيمة N أكبر من أو تساوي 1.",
            "order_whole_number": "ترتيب {stage} يجب أن يكون رقماً صحيحاً.",
            "duration_number": "مدة {stage} يجب أن تكون رقماً.",
            "order_range": "ترتيب {stage} يجب أن يكون 1 أو 2 أو 3.",
            "duration_negative": "مدة {stage} لا يمكن أن تكون سالبة.",
            "order_unique": "يجب أن تستخدم مراحل الاسترخاء والاستراحة واللعبة القيم 1 و2 و3 مرة واحدة لكل قيمة.",
            "game_duration_positive": "مدة اللعبة يجب أن تكون أكبر من الصفر.",
        },
    }
    STAGE_SESSION_LABELS = {"relax": "A", "break": "B", "game": "C"}

    _EXTRA_LANGUAGE_CODES = ("ko", "ja", "fr", "es", "ru", "it", "pt")
    _UI_LANGUAGE_OVERRIDES = {
        "ko": {
            "window_title": "EEG 분석",
            "tab_analyse": "분석",
            "tab_experiment": "실험 설정",
            "hero_title": "EEG 분석",
            "hero_subtitle": "CuongFX 제작",
            "idle": "대기",
            "disconnected": "연결 끊김",
            "connected": "장치 연결됨",
            "recording_off": "기록 안 함",
            "recording_on": "기록 중",
            "metric_connection": "연결",
            "metric_recording": "기록",
            "metric_battery": "배터리",
            "metric_hr": "심박수",
            "metric_stream_state": "스트림 상태",
            "metric_capture_mode": "캡처 모드",
            "metric_device_battery": "장치 배터리",
            "metric_battery_unavailable": "배터리 정보 없음",
            "metric_latest_estimate": "최신 추정치",
            "metric_live": "실시간",
            "metric_offline": "오프라인",
            "metric_standby": "대기",
            "connect_device": "장치 연결",
            "disconnect_device": "장치 연결 해제",
            "record_data": "데이터 기록",
            "stop_recording": "기록 중지",
            "start_game": "게임 시작",
            "play_demo": "데모 실행",
            "games_title": "게임",
            "examiner_control": "검사자 제어",
            "selected_device_none": "선택된 장치: 없음",
            "last_save_none": "저장된 기록 없음",
            "last_save_prefix": "최근 저장: ",
            "session_log": "세션 로그",
            "session_log_placeholder": "연결 이벤트, 기록 상태, 게임 실행 로그가 여기에 표시됩니다.",
            "stream_connected": "{name} 스트림 연결됨",
            "stream_waiting": "{name} 스트림 대기 중",
            "no_game_selected": "게임이 선택되지 않았습니다.",
            "game_auto_note": "장치가 연결되어 있고 기록이 꺼져 있으면 게임 시작 시 자동으로 기록을 시작합니다.",
            "no_device_recording": "먼저 장치를 연결하세요. Muse 스트림이 연결되어야 기록할 수 있습니다.",
            "start_game_no_device": "게임은 열리지만 장치가 연결되지 않아 EEG/PPG 기록 명령은 무시됩니다.",
            "record_data_title": "데이터 기록",
            "start_game_title": "게임 시작",
            "connect_device_title": "장치 연결",
            "disconnect_device_title": "장치 연결 해제",
            "examiner_default_subtitle": "게임 시작 전에 참가자 정보와 세션 세부사항을 설정하세요.",
            "field_name": "이름",
            "field_id": "ID",
            "field_id_hint": "Write only the ID number. Prefix P is added automatically to saved files.",
            "field_age": "나이",
            "field_n_value": "N 값",
            "field_note": "메모",
            "field_relax_audio": "휴식 중 음악 재생",
            "field_announcement_volume": "안내 음량",
            "planner_title": "세션 계획",
            "planner_session": "세션",
            "planner_order": "순서",
            "planner_duration": "시간 (분)",
            "stage_relax": "휴식",
            "stage_break": "쉬는 시간",
            "stage_game": "게임",
            "planner_help": "순서 1, 2, 3을 각각 한 번만 사용하세요. 단계 시간을 0으로 두면 건너뛰지만 게임은 0보다 커야 합니다.",
            "examiner_language": "언어: {language}",
            "name_required": "이름은 필수입니다.",
            "id_required": "ID는 필수입니다.",
            "age_required": "나이는 필수입니다.",
            "n_value_required": "N 값은 필수입니다.",
            "n_value_integer": "N 값은 정수여야 합니다.",
            "n_value_positive": "N 값은 1 이상이어야 합니다.",
            "order_whole_number": "{stage} 순서는 정수여야 합니다.",
            "duration_number": "{stage} 시간은 숫자여야 합니다.",
            "order_range": "{stage} 순서는 1, 2, 3 중 하나여야 합니다.",
            "duration_negative": "{stage} 시간은 음수일 수 없습니다.",
            "order_unique": "휴식, 쉬는 시간, 게임은 1, 2, 3을 각각 한 번씩 사용해야 합니다.",
            "game_duration_positive": "게임 시간은 0보다 커야 합니다.",
        },
        "ja": {
            "window_title": "EEG 解析",
            "tab_analyse": "解析",
            "tab_experiment": "実験設定",
            "hero_title": "EEG 解析",
            "hero_subtitle": "CuongFX により設計",
            "idle": "待機",
            "disconnected": "未接続",
            "connected": "デバイス接続済み",
            "recording_off": "未記録",
            "recording_on": "記録中",
            "metric_connection": "接続",
            "metric_recording": "記録",
            "metric_battery": "バッテリー",
            "metric_hr": "心拍数",
            "metric_stream_state": "ストリーム状態",
            "metric_capture_mode": "記録モード",
            "metric_device_battery": "デバイスバッテリー",
            "metric_battery_unavailable": "バッテリー情報なし",
            "metric_latest_estimate": "最新推定値",
            "metric_live": "ライブ",
            "metric_offline": "オフライン",
            "metric_standby": "待機",
            "connect_device": "デバイス接続",
            "disconnect_device": "デバイス切断",
            "record_data": "データ記録",
            "stop_recording": "記録停止",
            "start_game": "ゲーム開始",
            "play_demo": "デモ再生",
            "games_title": "ゲーム",
            "examiner_control": "試験者コントロール",
            "selected_device_none": "選択中のデバイス: なし",
            "last_save_none": "保存された記録はありません",
            "last_save_prefix": "最終保存: ",
            "session_log": "セッションログ",
            "session_log_placeholder": "接続イベント、記録状態、ゲーム起動ログがここに表示されます。",
            "stream_connected": "{name} ストリーム接続済み",
            "stream_waiting": "{name} ストリーム待機中",
            "no_game_selected": "ゲームが選択されていません。",
            "game_auto_note": "デバイス接続済みかつ未記録の場合、ゲーム開始時に自動で記録を開始します。",
            "no_device_recording": "先にデバイスを接続してください。Muse ストリーム接続後に記録できます。",
            "start_game_no_device": "ゲームは起動しますが、デバイス未接続のため EEG/PPG 記録コマンドは無視されます。",
            "record_data_title": "データ記録",
            "start_game_title": "ゲーム開始",
            "connect_device_title": "デバイス接続",
            "disconnect_device_title": "デバイス切断",
            "examiner_default_subtitle": "ゲーム開始前に参加者情報とセッション詳細を設定してください。",
            "field_name": "名前",
            "field_id": "ID",
            "field_id_hint": "Write only the ID number. Prefix P is added automatically to saved files.",
            "field_age": "年齢",
            "field_n_value": "N 値",
            "field_note": "メモ",
            "field_relax_audio": "Relax 中に音楽を再生",
            "field_announcement_volume": "案内音量",
            "planner_title": "セッション計画",
            "planner_session": "セッション",
            "planner_order": "順序",
            "planner_duration": "時間 (分)",
            "stage_relax": "Relax",
            "stage_break": "Break",
            "stage_game": "Game",
            "planner_help": "順序 1, 2, 3 をそれぞれ一度だけ使ってください。時間を 0 にするとその段階を飛ばしますが、Game は 0 より大きくする必要があります。",
            "examiner_language": "言語: {language}",
            "name_required": "名前は必須です。",
            "id_required": "ID は必須です。",
            "age_required": "年齢は必須です。",
            "n_value_required": "N 値は必須です。",
            "n_value_integer": "N 値は整数である必要があります。",
            "n_value_positive": "N 値は 1 以上である必要があります。",
            "order_whole_number": "{stage} の順序は整数である必要があります。",
            "duration_number": "{stage} の時間は数値である必要があります。",
            "order_range": "{stage} の順序は 1、2、3 のいずれかである必要があります。",
            "duration_negative": "{stage} の時間は負の値にできません。",
            "order_unique": "Relax、Break、Game では 1、2、3 をそれぞれ一度ずつ使う必要があります。",
            "game_duration_positive": "Game の時間は 0 より大きくする必要があります。",
        },
        "fr": {
            "window_title": "Analyse EEG",
            "tab_analyse": "Analyse",
            "tab_experiment": "Configuration de l'experience",
            "hero_title": "Analyse EEG",
            "hero_subtitle": "Concu par CuongFX",
            "idle": "Inactif",
            "disconnected": "Deconnecte",
            "connected": "Appareil connecte",
            "recording_off": "Pas d'enregistrement",
            "recording_on": "Enregistrement",
            "metric_connection": "Connexion",
            "metric_recording": "Enregistrement",
            "metric_battery": "Batterie",
            "metric_hr": "Frequence cardiaque",
            "metric_stream_state": "Etat du flux",
            "metric_capture_mode": "Mode de capture",
            "metric_device_battery": "Batterie appareil",
            "metric_battery_unavailable": "Batterie indisponible",
            "metric_latest_estimate": "Derniere estimation",
            "metric_live": "En direct",
            "metric_offline": "Hors ligne",
            "metric_standby": "Veille",
            "connect_device": "Connecter l'appareil",
            "disconnect_device": "Deconnecter l'appareil",
            "record_data": "Enregistrer les donnees",
            "stop_recording": "Arreter l'enregistrement",
            "start_game": "Demarrer le jeu",
            "play_demo": "Lancer la demo",
            "games_title": "Jeux",
            "examiner_control": "Controle examinateur",
            "selected_device_none": "Appareil selectionne: aucun",
            "last_save_none": "Aucun enregistrement sauvegarde",
            "last_save_prefix": "Derniere sauvegarde: ",
            "session_log": "Journal de session",
            "session_log_placeholder": "Les evenements de connexion, l'etat d'enregistrement et les lancements de jeu apparaissent ici.",
            "stream_connected": "Flux {name} connecte",
            "stream_waiting": "Flux {name} en attente",
            "no_game_selected": "Aucun jeu selectionne.",
            "game_auto_note": "Demarrer un jeu lance automatiquement l'enregistrement si un appareil est connecte et que l'enregistrement est inactif.",
            "no_device_recording": "Connectez d'abord un appareil. L'enregistrement fonctionne seulement apres connexion du flux Muse.",
            "start_game_no_device": "Le jeu va s'ouvrir, mais les commandes d'enregistrement EEG/PPG seront ignorees car aucun appareil n'est connecte.",
            "record_data_title": "Enregistrer les donnees",
            "start_game_title": "Demarrer le jeu",
            "connect_device_title": "Connecter l'appareil",
            "disconnect_device_title": "Deconnecter l'appareil",
            "examiner_default_subtitle": "Configurez les informations du participant et les details de session avant de lancer le jeu.",
            "field_name": "Nom",
            "field_id": "ID",
            "field_id_hint": "Write only the ID number. Prefix P is added automatically to saved files.",
            "field_age": "Age",
            "field_n_value": "Valeur N",
            "field_note": "Note",
            "field_relax_audio": "Lire de la musique pendant Relax",
            "field_announcement_volume": "Volume de l'annonce",
            "planner_title": "Planificateur de session",
            "planner_session": "Session",
            "planner_order": "Ordre",
            "planner_duration": "Duree (minutes)",
            "stage_relax": "Relax",
            "stage_break": "Pause",
            "stage_game": "Jeu",
            "planner_help": "Utilisez 1, 2 et 3 une seule fois chacun. Une duree de 0 saute l'etape, mais Game doit etre > 0.",
            "examiner_language": "Langue : {language}",
            "name_required": "Le nom est obligatoire.",
            "id_required": "L'ID est obligatoire.",
            "age_required": "L'age est obligatoire.",
            "n_value_required": "La valeur N est obligatoire.",
            "n_value_integer": "La valeur N doit etre un entier.",
            "n_value_positive": "La valeur N doit etre superieure ou egale a 1.",
            "order_whole_number": "L'ordre de {stage} doit etre un entier.",
            "duration_number": "La duree de {stage} doit etre un nombre.",
            "order_range": "L'ordre de {stage} doit etre 1, 2 ou 3.",
            "duration_negative": "La duree de {stage} ne peut pas etre negative.",
            "order_unique": "Relax, Pause et Jeu doivent utiliser 1, 2 et 3 exactement une fois.",
            "game_duration_positive": "La duree du jeu doit etre superieure a zero.",
        },
        "es": {
            "window_title": "Analisis EEG",
            "tab_analyse": "Analisis",
            "tab_experiment": "Configuracion del experimento",
            "hero_title": "Analisis EEG",
            "hero_subtitle": "Disenado por CuongFX",
            "idle": "Inactivo",
            "disconnected": "Desconectado",
            "connected": "Dispositivo conectado",
            "recording_off": "Sin grabacion",
            "recording_on": "Grabando",
            "metric_connection": "Conexion",
            "metric_recording": "Grabacion",
            "metric_battery": "Bateria",
            "metric_hr": "Frecuencia cardiaca",
            "metric_stream_state": "Estado del flujo",
            "metric_capture_mode": "Modo de captura",
            "metric_device_battery": "Bateria del dispositivo",
            "metric_battery_unavailable": "Bateria no disponible",
            "metric_latest_estimate": "Ultima estimacion",
            "metric_live": "En vivo",
            "metric_offline": "Sin conexion",
            "metric_standby": "En espera",
            "connect_device": "Conectar dispositivo",
            "disconnect_device": "Desconectar dispositivo",
            "record_data": "Grabar datos",
            "stop_recording": "Detener grabacion",
            "start_game": "Iniciar juego",
            "play_demo": "Iniciar demo",
            "games_title": "Juegos",
            "examiner_control": "Control del examinador",
            "selected_device_none": "Dispositivo seleccionado: ninguno",
            "last_save_none": "No hay grabacion guardada",
            "last_save_prefix": "Ultimo guardado: ",
            "session_log": "Registro de sesion",
            "session_log_placeholder": "Los eventos de conexion, estado de grabacion y lanzamientos de juego aparecen aqui.",
            "stream_connected": "Flujo {name} conectado",
            "stream_waiting": "Flujo {name} en espera",
            "no_game_selected": "Ningun juego seleccionado.",
            "game_auto_note": "Iniciar un juego comenzara automaticamente la grabacion si hay un dispositivo conectado y no se esta grabando.",
            "no_device_recording": "Conecta primero un dispositivo. La grabacion solo funciona cuando el flujo Muse esta conectado.",
            "start_game_no_device": "El juego se abrira, pero los comandos de grabacion EEG/PPG se ignoraran porque no hay dispositivo conectado.",
            "record_data_title": "Grabar datos",
            "start_game_title": "Iniciar juego",
            "connect_device_title": "Conectar dispositivo",
            "disconnect_device_title": "Desconectar dispositivo",
            "examiner_default_subtitle": "Configura la informacion del participante y los detalles de la sesion antes de iniciar el juego.",
            "field_name": "Nombre",
            "field_id": "ID",
            "field_id_hint": "Write only the ID number. Prefix P is added automatically to saved files.",
            "field_age": "Edad",
            "field_n_value": "Valor N",
            "field_note": "Nota",
            "field_relax_audio": "Reproducir música durante Relax",
            "field_announcement_volume": "Volumen del anuncio",
            "planner_title": "Planificador de sesion",
            "planner_session": "Sesion",
            "planner_order": "Orden",
            "planner_duration": "Duracion (minutos)",
            "stage_relax": "Relax",
            "stage_break": "Descanso",
            "stage_game": "Juego",
            "planner_help": "Usa 1, 2 y 3 exactamente una vez. Una duracion de 0 omite la etapa, pero Game debe ser mayor que 0.",
            "examiner_language": "Idioma: {language}",
            "name_required": "El nombre es obligatorio.",
            "id_required": "El ID es obligatorio.",
            "age_required": "La edad es obligatoria.",
            "n_value_required": "El valor N es obligatorio.",
            "n_value_integer": "El valor N debe ser un numero entero.",
            "n_value_positive": "El valor N debe ser al menos 1.",
            "order_whole_number": "El orden de {stage} debe ser un numero entero.",
            "duration_number": "La duracion de {stage} debe ser un numero.",
            "order_range": "El orden de {stage} debe ser 1, 2 o 3.",
            "duration_negative": "La duracion de {stage} no puede ser negativa.",
            "order_unique": "Relax, Descanso y Juego deben usar 1, 2 y 3 exactamente una vez.",
            "game_duration_positive": "La duracion del juego debe ser mayor que cero.",
        },
        "ru": {
            "window_title": "EEG Анализ",
            "tab_analyse": "Анализ",
            "tab_experiment": "Настройка эксперимента",
            "hero_title": "EEG Анализ",
            "hero_subtitle": "Разработано CuongFX",
            "idle": "Ожидание",
            "disconnected": "Отключено",
            "connected": "Устройство подключено",
            "recording_off": "Не записывается",
            "recording_on": "Запись",
            "metric_connection": "Подключение",
            "metric_recording": "Запись",
            "metric_battery": "Батарея",
            "metric_hr": "Пульс",
            "metric_stream_state": "Состояние потока",
            "metric_capture_mode": "Режим записи",
            "metric_device_battery": "Батарея устройства",
            "metric_battery_unavailable": "Батарея недоступна",
            "metric_latest_estimate": "Последняя оценка",
            "metric_live": "Онлайн",
            "metric_offline": "Офлайн",
            "metric_standby": "Ожидание",
            "connect_device": "Подключить устройство",
            "disconnect_device": "Отключить устройство",
            "record_data": "Запись данных",
            "stop_recording": "Остановить запись",
            "start_game": "Запустить игру",
            "play_demo": "Запустить демо",
            "games_title": "Игры",
            "examiner_control": "Панель экзаменатора",
            "selected_device_none": "Выбранное устройство: нет",
            "last_save_none": "Сохраненных записей нет",
            "last_save_prefix": "Последнее сохранение: ",
            "session_log": "Журнал сессии",
            "session_log_placeholder": "События подключения, состояние записи и запуск игр отображаются здесь.",
            "stream_connected": "Поток {name} подключен",
            "stream_waiting": "Поток {name} ожидает",
            "no_game_selected": "Игра не выбрана.",
            "game_auto_note": "При запуске игры запись начнется автоматически, если устройство подключено и запись не активна.",
            "no_device_recording": "Сначала подключите устройство. Запись работает только после подключения потока Muse.",
            "start_game_no_device": "Игра откроется, но команды записи EEG/PPG будут игнорироваться, так как устройство не подключено.",
            "record_data_title": "Запись данных",
            "start_game_title": "Запуск игры",
            "connect_device_title": "Подключить устройство",
            "disconnect_device_title": "Отключить устройство",
            "examiner_default_subtitle": "Настройте данные участника и параметры сессии перед запуском игры.",
            "field_name": "Имя",
            "field_id": "ID",
            "field_id_hint": "Write only the ID number. Prefix P is added automatically to saved files.",
            "field_age": "Возраст",
            "field_n_value": "Значение N",
            "field_note": "Заметка",
            "field_relax_audio": "Воспроизводить музыку во время Relax",
            "field_announcement_volume": "Громкость сигнала",
            "planner_title": "План сессии",
            "planner_session": "Сессия",
            "planner_order": "Порядок",
            "planner_duration": "Длительность (минуты)",
            "stage_relax": "Relax",
            "stage_break": "Перерыв",
            "stage_game": "Игра",
            "planner_help": "Используйте 1, 2 и 3 ровно по одному разу. Длительность 0 пропускает этап, но Game должна быть больше 0.",
            "examiner_language": "Язык: {language}",
            "name_required": "Имя обязательно.",
            "id_required": "ID обязателен.",
            "age_required": "Возраст обязателен.",
            "n_value_required": "Значение N обязательно.",
            "n_value_integer": "Значение N должно быть целым числом.",
            "n_value_positive": "Значение N должно быть не меньше 1.",
            "order_whole_number": "Порядок для {stage} должен быть целым числом.",
            "duration_number": "Длительность для {stage} должна быть числом.",
            "order_range": "Порядок для {stage} должен быть 1, 2 или 3.",
            "duration_negative": "Длительность для {stage} не может быть отрицательной.",
            "order_unique": "Relax, Перерыв и Игра должны использовать 1, 2 и 3 ровно по одному разу.",
            "game_duration_positive": "Длительность игры должна быть больше нуля.",
        },
        "it": {
            "window_title": "Analisi EEG",
            "tab_analyse": "Analisi",
            "tab_experiment": "Impostazione esperimento",
            "hero_title": "Analisi EEG",
            "hero_subtitle": "Progettato da CuongFX",
            "idle": "Inattivo",
            "disconnected": "Disconnesso",
            "connected": "Dispositivo connesso",
            "recording_off": "Nessuna registrazione",
            "recording_on": "Registrazione",
            "metric_connection": "Connessione",
            "metric_recording": "Registrazione",
            "metric_battery": "Batteria",
            "metric_hr": "Frequenza cardiaca",
            "metric_stream_state": "Stato stream",
            "metric_capture_mode": "Modalita acquisizione",
            "metric_device_battery": "Batteria dispositivo",
            "metric_battery_unavailable": "Batteria non disponibile",
            "metric_latest_estimate": "Ultima stima",
            "metric_live": "Live",
            "metric_offline": "Offline",
            "metric_standby": "Standby",
            "connect_device": "Connetti dispositivo",
            "disconnect_device": "Disconnetti dispositivo",
            "record_data": "Registra dati",
            "stop_recording": "Ferma registrazione",
            "start_game": "Avvia gioco",
            "play_demo": "Avvia demo",
            "games_title": "Giochi",
            "examiner_control": "Controllo esaminatore",
            "selected_device_none": "Dispositivo selezionato: nessuno",
            "last_save_none": "Nessuna registrazione salvata",
            "last_save_prefix": "Ultimo salvataggio: ",
            "session_log": "Log sessione",
            "session_log_placeholder": "Eventi di connessione, stato registrazione e avvii gioco appaiono qui.",
            "stream_connected": "Stream {name} connesso",
            "stream_waiting": "Stream {name} in attesa",
            "no_game_selected": "Nessun gioco selezionato.",
            "game_auto_note": "L'avvio di un gioco avviera automaticamente la registrazione se un dispositivo e gia connesso e la registrazione non e attiva.",
            "no_device_recording": "Connetti prima un dispositivo. La registrazione funziona solo dopo la connessione dello stream Muse.",
            "start_game_no_device": "Il gioco si aprira, ma i comandi di registrazione EEG/PPG saranno ignorati perche nessun dispositivo e connesso.",
            "record_data_title": "Registra dati",
            "start_game_title": "Avvia gioco",
            "connect_device_title": "Connetti dispositivo",
            "disconnect_device_title": "Disconnetti dispositivo",
            "examiner_default_subtitle": "Configura le informazioni del partecipante e i dettagli della sessione prima di avviare il gioco.",
            "field_name": "Nome",
            "field_id": "ID",
            "field_id_hint": "Write only the ID number. Prefix P is added automatically to saved files.",
            "field_age": "Eta",
            "field_n_value": "Valore N",
            "field_note": "Nota",
            "field_relax_audio": "Riproduci musica durante Relax",
            "field_announcement_volume": "Volume annuncio",
            "planner_title": "Pianificatore sessione",
            "planner_session": "Sessione",
            "planner_order": "Ordine",
            "planner_duration": "Durata (minuti)",
            "stage_relax": "Relax",
            "stage_break": "Pausa",
            "stage_game": "Gioco",
            "planner_help": "Usa 1, 2 e 3 una sola volta ciascuno. Una durata di 0 salta la fase, ma Game deve essere maggiore di 0.",
            "examiner_language": "Lingua: {language}",
            "name_required": "Il nome e obbligatorio.",
            "id_required": "L'ID e obbligatorio.",
            "age_required": "L'eta e obbligatoria.",
            "n_value_required": "Il valore N e obbligatorio.",
            "n_value_integer": "Il valore N deve essere un numero intero.",
            "n_value_positive": "Il valore N deve essere almeno 1.",
            "order_whole_number": "L'ordine di {stage} deve essere un numero intero.",
            "duration_number": "La durata di {stage} deve essere un numero.",
            "order_range": "L'ordine di {stage} deve essere 1, 2 o 3.",
            "duration_negative": "La durata di {stage} non puo essere negativa.",
            "order_unique": "Relax, Pausa e Gioco devono usare 1, 2 e 3 esattamente una volta.",
            "game_duration_positive": "La durata del gioco deve essere maggiore di zero.",
        },
        "pt": {
            "window_title": "Analise EEG",
            "tab_analyse": "Analise",
            "tab_experiment": "Configuracao do experimento",
            "hero_title": "Analise EEG",
            "hero_subtitle": "Projetado por CuongFX",
            "idle": "Inativo",
            "disconnected": "Desconectado",
            "connected": "Dispositivo conectado",
            "recording_off": "Sem gravacao",
            "recording_on": "Gravando",
            "metric_connection": "Conexao",
            "metric_recording": "Gravacao",
            "metric_battery": "Bateria",
            "metric_hr": "Frequencia cardiaca",
            "metric_stream_state": "Estado do stream",
            "metric_capture_mode": "Modo de captura",
            "metric_device_battery": "Bateria do dispositivo",
            "metric_battery_unavailable": "Bateria indisponivel",
            "metric_latest_estimate": "Ultima estimativa",
            "metric_live": "Ao vivo",
            "metric_offline": "Offline",
            "metric_standby": "Espera",
            "connect_device": "Conectar dispositivo",
            "disconnect_device": "Desconectar dispositivo",
            "record_data": "Gravar dados",
            "stop_recording": "Parar gravacao",
            "start_game": "Iniciar jogo",
            "play_demo": "Iniciar demo",
            "games_title": "Jogos",
            "examiner_control": "Controle do examinador",
            "selected_device_none": "Dispositivo selecionado: nenhum",
            "last_save_none": "Nenhuma gravacao salva",
            "last_save_prefix": "Ultimo salvamento: ",
            "session_log": "Log da sessao",
            "session_log_placeholder": "Eventos de conexao, estado de gravacao e inicializacoes de jogo aparecem aqui.",
            "stream_connected": "Stream {name} conectado",
            "stream_waiting": "Stream {name} aguardando",
            "no_game_selected": "Nenhum jogo selecionado.",
            "game_auto_note": "Iniciar um jogo comeca automaticamente a gravacao se um dispositivo estiver conectado e a gravacao nao estiver ativa.",
            "no_device_recording": "Conecte um dispositivo primeiro. A gravacao so funciona apos o stream Muse estar conectado.",
            "start_game_no_device": "O jogo sera aberto, mas os comandos de gravacao EEG/PPG serao ignorados porque nao ha dispositivo conectado.",
            "record_data_title": "Gravar dados",
            "start_game_title": "Iniciar jogo",
            "connect_device_title": "Conectar dispositivo",
            "disconnect_device_title": "Desconectar dispositivo",
            "examiner_default_subtitle": "Configure as informacoes do participante e os detalhes da sessao antes de iniciar o jogo.",
            "field_name": "Nome",
            "field_id": "ID",
            "field_id_hint": "Write only the ID number. Prefix P is added automatically to saved files.",
            "field_age": "Idade",
            "field_n_value": "Valor N",
            "field_note": "Nota",
            "field_relax_audio": "Tocar música durante Relax",
            "field_announcement_volume": "Volume do anuncio",
            "planner_title": "Planejador de sessao",
            "planner_session": "Sessao",
            "planner_order": "Ordem",
            "planner_duration": "Duracao (minutos)",
            "stage_relax": "Relax",
            "stage_break": "Pausa",
            "stage_game": "Jogo",
            "planner_help": "Use 1, 2 e 3 exatamente uma vez cada. Duracao 0 ignora a etapa, mas Game deve ser maior que 0.",
            "examiner_language": "Idioma: {language}",
            "name_required": "O nome e obrigatorio.",
            "id_required": "O ID e obrigatorio.",
            "age_required": "A idade e obrigatoria.",
            "n_value_required": "O valor N e obrigatorio.",
            "n_value_integer": "O valor N deve ser um numero inteiro.",
            "n_value_positive": "O valor N deve ser pelo menos 1.",
            "order_whole_number": "A ordem de {stage} deve ser um numero inteiro.",
            "duration_number": "A duracao de {stage} deve ser um numero.",
            "order_range": "A ordem de {stage} deve ser 1, 2 ou 3.",
            "duration_negative": "A duracao de {stage} nao pode ser negativa.",
            "order_unique": "Relax, Pausa e Jogo devem usar 1, 2 e 3 exatamente uma vez.",
            "game_duration_positive": "A duracao do jogo deve ser maior que zero.",
        },
    }
    for _code in _EXTRA_LANGUAGE_CODES:
        _bundle = dict(UI_TRANSLATIONS["en"])
        _bundle.update(_UI_LANGUAGE_OVERRIDES.get(_code, {}))
        UI_TRANSLATIONS[_code] = _bundle
    del _code, _bundle

    _RELAX_MUSIC_ITEMS = (
        ("binaural_sound", "music_binaural_sound"),
        ("rain_sound", "music_rain_sound"),
    )

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
        self._responsive_signature: tuple[int, int] | None = None
        self.timer = QTimer(self)
        self.game_languages = {
            "en": "English",
            "de": "German",
            "vi": "Tiếng Việt",
            "zh": "中文",
            "ar": "العربية",
            "ko": "한국어",
            "ja": "日本語",
            "fr": "Français",
            "es": "Español",
            "ru": "Русский",
            "it": "Italiano",
            "pt": "Português",
        }
        self.software_languages = {
            "en": ("🇬🇧 English", "English"),
            "de": ("🇩🇪 Deutsch", "Deutsch"),
            "vi": ("🇻🇳 Tiếng Việt", "Tiếng Việt"),
            "zh": ("🇨🇳 中文", "中文"),
            "ar": ("🇸🇦 العربية", "العربية"),
            "ko": ("🇰🇷 한국어", "한국어"),
            "ja": ("🇯🇵 日本語", "日本語"),
            "fr": ("🇫🇷 Français", "Français"),
            "es": ("🇪🇸 Español", "Español"),
            "ru": ("🇷🇺 Русский", "Русский"),
            "it": ("🇮🇹 Italiano", "Italiano"),
            "pt": ("🇵🇹 Português", "Português"),
        }
        self.software_language_code = "en"
        self.afplay_command = shutil.which("afplay")
        self.preview_sound_path = self._resolve_preview_sound_path()
        self.announcement_preview_timer = QTimer(self)
        self.announcement_preview_timer.setSingleShot(True)
        self.announcement_preview_timer.timeout.connect(self._play_announcement_preview_sound)

        self._setup_window()
        self._build_ui()
        self._connect_events()
        self._apply_software_language()
        self._load_form_defaults()
        self._apply_responsive_layout(force=True)
        self.timer.start(self.config.plot_update_interval_ms)

    def _ui(self, key: str, **kwargs) -> str:
        text = self.UI_TRANSLATIONS.get(self.software_language_code, self.UI_TRANSLATIONS["en"]).get(
            key,
            self.UI_TRANSLATIONS["en"].get(key, key),
        )
        return text.format(**kwargs) if kwargs else text

    def _stage_label(self, stage_key: str) -> str:
        return f"{self._ui(f'stage_{stage_key}')} ({self.STAGE_SESSION_LABELS.get(stage_key, '?')})"

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
            self.relax_music_label.setText(self._ui("field_relax_audio"))
            self.music_track_label.setText(self._ui("field_music_track"))
            self._refresh_music_track_combo_labels()
            self._update_relax_music_switch_text()
            self.announcement_volume_label.setText(self._ui("field_announcement_volume"))
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
            self._update_selected_game_panels()
            self._refresh_ui()

    def _setup_window(self) -> None:
        self.setWindowTitle(self._ui("window_title"))
        self.resize(1480, 960)
        self.setMinimumSize(720, 520)
        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Window, QColor("#f5efe6"))
        palette.setColor(QPalette.ColorRole.WindowText, QColor("#1f2937"))
        palette.setColor(QPalette.ColorRole.Base, QColor("#fffdf8"))
        palette.setColor(QPalette.ColorRole.Text, QColor("#1f2937"))
        self.setPalette(palette)
        self._apply_responsive_styles(force=True)

    @staticmethod
    def _clamp_int(value: float, minimum: int, maximum: int) -> int:
        return max(minimum, min(maximum, int(round(value))))

    def _responsive_scale(self) -> float:
        width_scale = self.width() / 1480.0
        height_scale = self.height() / 960.0
        return max(0.84, min(1.0, min(width_scale, height_scale)))

    def _apply_responsive_styles(self, *, force: bool = False) -> None:
        scale = self._responsive_scale()
        signature = (int(scale * 100), max(720, self.width()) // 80)
        if not force and signature == self._responsive_signature:
            return
        self._responsive_signature = signature

        ui_scale = min(scale, 1.0)
        hero_radius = self._clamp_int(30 * ui_scale, 22, 34)
        card_radius = self._clamp_int(24 * ui_scale, 18, 28)
        badge_radius = self._clamp_int(18 * ui_scale, 14, 22)
        combo_radius = self._clamp_int(16 * ui_scale, 12, 20)
        input_radius = self._clamp_int(14 * ui_scale, 11, 18)
        hero_title_size = self._clamp_int(28 * ui_scale, 22, 28)
        hero_subtitle_size = self._clamp_int(13 * ui_scale, 11, 13)
        section_title_size = self._clamp_int(16 * ui_scale, 14, 16)
        body_size = self._clamp_int(12 * ui_scale, 11, 12)
        small_size = self._clamp_int(11 * ui_scale, 10, 11)
        metric_value_size = self._clamp_int(22 * ui_scale, 18, 22)
        examiner_heading_size = self._clamp_int(14 * ui_scale, 12, 14)
        button_height = self._clamp_int(46 * ui_scale, 40, 46)
        combo_height = self._clamp_int(42 * ui_scale, 36, 42)
        dropdown_width = self._clamp_int(28 * ui_scale, 22, 28)
        list_item_height = self._clamp_int(32 * ui_scale, 28, 34)
        card_padding_v = self._clamp_int(12 * ui_scale, 10, 12)
        card_padding_h = self._clamp_int(16 * ui_scale, 14, 16)
        language_height = self._clamp_int(28 * ui_scale, 26, 30)
        tab_pad_v = self._clamp_int(10 * ui_scale, 9, 10)
        tab_pad_h = self._clamp_int(20 * ui_scale, 16, 20)
        item_radius = self._clamp_int(input_radius * 0.75, 8, 14)
        compact_height = self._clamp_int(36 * ui_scale, 32, 36)
        compact_button_height = self._clamp_int(40 * ui_scale, 36, 40)
        compact_padding_v = self._clamp_int(9 * ui_scale, 8, 9)
        compact_padding_h = self._clamp_int(12 * ui_scale, 10, 12)

        self.setStyleSheet(
            f"""
            QWidget#Root {{
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 1,
                    stop: 0 #faf6ef,
                    stop: 0.55 #f7fbfc,
                    stop: 1 #eef7f5
                );
            }}
            QFrame#HeroCard {{
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 #1f2937,
                    stop: 0.5 #134e4a,
                    stop: 1 #0f766e
                );
                border-radius: {hero_radius}px;
            }}
            QFrame#SidebarCard, QFrame#MetricCard, QFrame#PlotCard {{
                background: rgba(255, 252, 246, 0.96);
                border: 1px solid #e8dccb;
                border-radius: {card_radius}px;
            }}
            QFrame#InsetPanel {{
                background: rgba(248, 244, 236, 0.96);
                border: 1px solid #eee1cf;
                border-radius: {self._clamp_int(card_radius * 0.78, 14, 22)}px;
            }}
            QLabel#HeroTitle {{
                color: #fff8ee;
                font-size: {hero_title_size}px;
                font-weight: 800;
            }}
            QLabel#HeroSubtitle {{
                color: rgba(255, 248, 238, 0.84);
                font-size: {hero_subtitle_size}px;
            }}
            QLabel#SectionTitle, QLabel#DialogTitle {{
                color: #111827;
                font-size: {section_title_size}px;
                font-weight: 800;
            }}
            QLabel#DialogText, QLabel#DialogStatus, QLabel#SupportText {{
                color: #5b6472;
                font-size: {body_size}px;
            }}
            QLabel#CardLead {{
                color: #64748b;
                font-size: {body_size}px;
                font-weight: 600;
            }}
            QLabel#MetricTitle {{
                color: #6b7280;
                font-size: {small_size}px;
                font-weight: 700;
            }}
            QLabel#MetricValue {{
                font-size: {metric_value_size}px;
                font-weight: 900;
            }}
            QLabel#MetricCaption {{
                color: #6b7280;
                font-size: {small_size}px;
            }}
            QLabel#ExaminerHeading {{
                color: #0f172a;
                font-size: {examiner_heading_size}px;
                font-weight: 800;
            }}
            QLabel#ExaminerBody {{
                color: #5b6472;
                font-size: {body_size}px;
                line-height: 1.45em;
            }}
            QLabel#FieldLabel {{
                color: #334155;
                font-size: {small_size}px;
                font-weight: 800;
            }}
            QLabel#RelaxMusicSwitchCaption {{
                color: #475569;
                font-size: {body_size}px;
                font-weight: 700;
                min-width: 28px;
            }}
            QLabel#PlannerHeader {{
                color: #64748b;
                font-size: {small_size}px;
                font-weight: 800;
            }}
            QLabel#InsetTitle {{
                color: #0f172a;
                font-size: {small_size}px;
                font-weight: 800;
                letter-spacing: 0.02em;
            }}
            QCheckBox {{
                color: #334155;
                font-size: {body_size}px;
                font-weight: 700;
                spacing: 8px;
            }}
            QPushButton#PrimaryButton {{
                background: #0f766e;
                color: white;
                border: none;
                border-radius: {combo_radius}px;
                padding: {card_padding_v}px {card_padding_h}px;
                font-weight: 800;
                min-height: {button_height}px;
            }}
            QPushButton#PrimaryButton:hover {{
                background: #115e59;
            }}
            QPushButton#AccentButton {{
                background: #f97316;
                color: white;
                border: none;
                border-radius: {combo_radius}px;
                padding: {card_padding_v}px {card_padding_h}px;
                font-weight: 800;
                min-height: {button_height}px;
            }}
            QPushButton#AccentButton:hover {{
                background: #ea580c;
            }}
            QPushButton#SecondaryButton {{
                background: #fffdf8;
                color: #1f2937;
                border: 1px solid #d9c6ae;
                border-radius: {combo_radius}px;
                padding: {card_padding_v}px {card_padding_h}px;
                font-weight: 700;
                min-height: {button_height}px;
            }}
            QPushButton#SecondaryButton:hover {{
                background: #fff5ea;
            }}
            QPushButton:disabled {{
                background: #e7dfd5;
                color: #9ca3af;
                border-color: #e7dfd5;
            }}
            QPlainTextEdit#LogOutput, QListWidget {{
                background: #fffdf9;
                color: #1f2937;
                border: 1px solid #eadfce;
                border-radius: {badge_radius}px;
                padding: 12px;
                font-size: {body_size}px;
            }}
            QComboBox {{
                background: #fffdf8;
                color: #1f2937;
                border: 1px solid #d9c6ae;
                border-radius: {combo_radius}px;
                padding: 10px 12px;
                font-size: {body_size}px;
                min-height: {combo_height}px;
            }}
            QComboBox:hover {{
                border: 1px solid #0f766e;
                background: #fffaf2;
            }}
            QComboBox::drop-down {{
                border: none;
                width: {dropdown_width}px;
            }}
            QComboBox#SoftwareLanguageCombo {{
                background: #d1fae5;
                color: #064e3b;
                border: 1px solid #99f6e4;
                border-radius: {input_radius}px;
                padding: 3px 10px;
                font-size: {small_size}px;
                font-weight: 800;
                min-height: {language_height}px;
            }}
            QComboBox#SoftwareLanguageCombo:hover {{
                background: #ccfbf1;
                border: 1px solid #99f6e4;
            }}
            QComboBox#SoftwareLanguageCombo::drop-down {{
                width: 18px;
            }}
            QComboBox QAbstractItemView {{
                background: #fffdf9;
                color: #1f2937;
                border: 1px solid #e3d5c3;
                border-radius: {input_radius}px;
                outline: 0;
                padding: 6px;
                selection-background-color: #dff7f2;
                selection-color: #0f172a;
            }}
            QComboBox QAbstractItemView::item {{
                min-height: {list_item_height}px;
                padding: 8px 10px;
                margin: 2px 0;
                border-radius: {item_radius}px;
                color: #1f2937;
                background: transparent;
            }}
            QComboBox QAbstractItemView::item:hover {{
                background: #fff1dc;
                color: #111827;
            }}
            QComboBox QAbstractItemView::item:selected {{
                background: #dff7f2;
                color: #0f172a;
            }}
            QLineEdit, QTextEdit {{
                background: #fffdf8;
                color: #1f2937;
                border: 1px solid #d9c6ae;
                border-radius: {input_radius}px;
                padding: 10px 12px;
                font-size: {body_size}px;
            }}
            QLineEdit:focus, QTextEdit:focus, QComboBox:focus {{
                border: 1px solid #0f766e;
            }}
            QComboBox[compact="true"], QLineEdit[compact="true"], QTextEdit[compact="true"] {{
                border-radius: {self._clamp_int(input_radius * 0.92, 10, 16)}px;
                padding: {self._clamp_int(8 * ui_scale, 7, 9)}px {self._clamp_int(10 * ui_scale, 9, 11)}px;
                font-size: {self._clamp_int((body_size - 1), 10, 13)}px;
            }}
            QComboBox[compact="true"], QLineEdit[compact="true"] {{
                min-height: {compact_height}px;
            }}
            QTextEdit[compact="true"] {{
                padding-top: {self._clamp_int(9 * ui_scale, 8, 10)}px;
            }}
            QPushButton[compact="true"] {{
                border-radius: {self._clamp_int(combo_radius * 0.92, 11, 18)}px;
                padding: {compact_padding_v}px {compact_padding_h}px;
                min-height: {compact_button_height}px;
            }}
            QSlider::groove:horizontal {{
                height: 8px;
                background: #d8dee7;
                border-radius: 4px;
            }}
            QSlider::sub-page:horizontal {{
                background: #0ea5a2;
                border-radius: 4px;
            }}
            QSlider::handle:horizontal {{
                width: 12px;
                background: #fffdf8;
                border: 1px solid #94a3b8;
                border-radius: 6px;
                margin: -2px 0;
            }}
            QTabWidget::pane {{
                border: 1px solid #e8dccb;
                border-radius: {card_radius}px;
                background: rgba(255, 252, 246, 0.72);
                margin-top: 10px;
            }}
            QTabBar::tab {{
                background: rgba(255, 249, 240, 0.82);
                color: #5b6472;
                border: 1px solid #e8dccb;
                border-bottom: none;
                border-top-left-radius: {combo_radius}px;
                border-top-right-radius: {combo_radius}px;
                padding: {tab_pad_v}px {tab_pad_h}px;
                margin-right: 6px;
                font-weight: 700;
            }}
            QTabBar::tab:selected {{
                background: #fffdf8;
                color: #0f172a;
            }}
            QTabBar::tab:hover:!selected {{
                background: #fff7eb;
                color: #1f2937;
            }}
            """
        )

    def _apply_responsive_layout(self, *, force: bool = False) -> None:
        self._apply_responsive_styles(force=force)
        if not hasattr(self, "signal_area_widget"):
            return

        scale = self._responsive_scale()
        width = max(self.width(), 720)
        height = max(self.height(), 520)

        if hasattr(self, "root_page_layout"):
            margin = self._clamp_int(20 * scale, 12, 28)
            self.root_page_layout.setContentsMargins(margin, margin, margin, margin)
            self.root_page_layout.setSpacing(self._clamp_int(18 * scale, 12, 24))
        if hasattr(self, "header_layout"):
            margin = self._clamp_int(18 * scale, 14, 24)
            self.header_layout.setContentsMargins(margin, margin, margin, margin)
            self.header_layout.setSpacing(self._clamp_int(22 * scale, 16, 30))

        metric_height = self._clamp_int(82 * scale, 76, 112)
        for card in self.metric_card_widgets:
            card.setMinimumHeight(metric_height)

        if hasattr(self, "software_language_combo"):
            self.software_language_combo.setFixedWidth(self._clamp_int(width * 0.105, 126, 176))
        if hasattr(self, "connect_button"):
            sidebar_button_height = self._clamp_int(height * 0.05, 38, 54)
            self.connect_button.setMinimumHeight(sidebar_button_height)
            self.connect_button.setMaximumHeight(sidebar_button_height)
            self.disconnect_button.setMinimumHeight(sidebar_button_height)
            self.disconnect_button.setMaximumHeight(sidebar_button_height)
            self.record_button.setMinimumHeight(sidebar_button_height)
            self.record_button.setMaximumHeight(sidebar_button_height)
        if hasattr(self, "launch_game_button"):
            game_panel_width = (
                self.game_card_widget.width()
                if hasattr(self, "game_card_widget")
                else width * 0.24
            )
            button_width = self._clamp_int(game_panel_width * 0.74, 160, 220)
            self.launch_game_button.setMinimumWidth(button_width)
            self.play_demo_button.setMinimumWidth(button_width)
        if hasattr(self, "examiner_note_input"):
            note_height = self._clamp_int(height * 0.07, 64, 78)
            self.examiner_note_input.setMinimumHeight(note_height)
            self.examiner_note_input.setMaximumHeight(note_height)
        if hasattr(self, "examiner_n_value_input"):
            examiner_width = self.examiner_card_widget.width() if hasattr(self, "examiner_card_widget") else width
            self.examiner_n_value_input.setMaximumWidth(self._clamp_int(examiner_width * 0.32, 92, 148))
        if hasattr(self, "log_output"):
            self.log_output.setMinimumHeight(self._clamp_int(height * 0.18, 96, 220))
        if hasattr(self, "experiment_content_widget"):
            self.experiment_content_widget.setMaximumWidth(self._clamp_int(width * 0.96, 980, 1660))

        planner_width = self.planner_card_widget.width() if hasattr(self, "planner_card_widget") else width
        for input_widget in getattr(self, "stage_order_inputs", {}).values():
            input_widget.setMaximumWidth(self._clamp_int(planner_width * 0.18, 58, 84))
        for input_widget in getattr(self, "stage_duration_inputs", {}).values():
            input_widget.setMaximumWidth(self._clamp_int(planner_width * 0.22, 74, 104))

        self._relayout_experiment_tab()
        self._relayout_signal_area()

    def _build_ui(self) -> None:
        root = QWidget()
        root.setObjectName("Root")
        root.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setCentralWidget(root)

        page = QVBoxLayout(root)
        self.root_page_layout = page
        page.setContentsMargins(20, 20, 20, 20)
        page.setSpacing(18)
        page.addWidget(self._build_header())
        page.addWidget(self._build_tabs(), stretch=1)

    def _build_tabs(self) -> QTabWidget:
        self.tabs_widget = QTabWidget()
        self.tabs_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.tabs_widget.addTab(self._build_analyse_tab(), self._ui("tab_analyse"))
        self.tabs_widget.addTab(self._build_experiment_tab(), self._ui("tab_experiment"))
        return self.tabs_widget

    def _build_analyse_tab(self) -> QWidget:
        container = QWidget()
        container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.analyse_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.analyse_splitter.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.analyse_splitter.setChildrenCollapsible(False)
        self.analyse_splitter.addWidget(self._build_signal_area())
        self.analyse_splitter.addWidget(self._build_analyse_sidebar())
        self.analyse_splitter.setStretchFactor(0, 5)
        self.analyse_splitter.setStretchFactor(1, 2)
        self.analyse_splitter.splitterMoved.connect(lambda _pos, _index: self._relayout_signal_area())
        layout.addWidget(self.analyse_splitter, stretch=1)
        QTimer.singleShot(0, self._set_initial_analyse_splitter_sizes)
        return container

    def _build_experiment_tab(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        shell = QWidget()
        shell_layout = QHBoxLayout(shell)
        shell_layout.setContentsMargins(0, 0, 0, 0)
        shell_layout.setSpacing(0)
        shell_layout.addStretch(1)
        content = QWidget()
        self.experiment_content_widget = content
        content.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        content.setMinimumWidth(980)
        content.setMaximumWidth(1660)
        layout = QVBoxLayout(content)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        game_card = self._build_game_card()
        game_card.setMinimumWidth(280)
        game_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        examiner_card = self._build_examiner_details_card()
        examiner_card.setMinimumWidth(280)
        examiner_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        planner_card = self._build_session_planner_card()
        planner_card.setMinimumWidth(280)
        planner_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.game_card_widget = game_card
        self.examiner_card_widget = examiner_card
        self.planner_card_widget = planner_card
        cards_grid = QGridLayout()
        self.experiment_cards_grid = cards_grid
        cards_grid.setContentsMargins(0, 0, 0, 0)
        cards_grid.setHorizontalSpacing(12)
        cards_grid.setVerticalSpacing(12)
        layout.addLayout(cards_grid, stretch=1)
        shell_layout.addWidget(content)
        shell_layout.addStretch(1)
        self._update_selected_game_panels()
        QTimer.singleShot(0, self._relayout_experiment_tab)
        scroll.setWidget(shell)
        return scroll

    def _set_initial_analyse_splitter_sizes(self) -> None:
        if not hasattr(self, "analyse_splitter"):
            return
        total = max(400, self.analyse_splitter.width())
        left_ratio = 0.69 if total >= 1260 else 0.66
        left = int(total * left_ratio)
        right = max(280, total - left)
        self.analyse_splitter.setSizes([left, right])

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
        self.header_layout = layout
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
        self.software_language_combo.setFixedWidth(138)
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
        sidebar = QWidget()
        sidebar.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        layout.addWidget(self._build_device_card())
        layout.addWidget(self._build_log_card(), stretch=1)
        return sidebar

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
        self.connect_button.setProperty("compact", True)
        self.connect_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.disconnect_button = QPushButton(self._ui("disconnect_device"))
        self.disconnect_button.setObjectName("SecondaryButton")
        self.disconnect_button.setProperty("compact", True)
        self.disconnect_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout.addWidget(self.connect_button)
        layout.addWidget(self.disconnect_button)

        self.record_button = QPushButton(self._ui("record_data"))
        self.record_button.setObjectName("AccentButton")
        self.record_button.setProperty("compact", True)
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
        return card

    def _build_game_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("SidebarCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(12)

        self.games_card_title = QLabel(self._ui("games_title"))
        self.games_card_title.setObjectName("SectionTitle")
        layout.addWidget(self.games_card_title)

        self.game_combo = QComboBox()
        self.game_combo.setProperty("compact", True)
        self.game_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        for game in self.game_registry.list_games():
            self.game_combo.addItem(game.title, game.game_id)
        layout.addWidget(self.game_combo)

        self.game_language_combo = QComboBox()
        self.game_language_combo.setProperty("compact", True)
        self.game_language_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout.addWidget(self.game_language_combo)

        self.game_description_label = QLabel()
        self.game_description_label.setObjectName("CardLead")
        self.game_description_label.setWordWrap(True)
        layout.addWidget(self.game_description_label)

        self.launch_game_button = QPushButton(self._ui("start_game"))
        self.launch_game_button.setObjectName("PrimaryButton")
        self.launch_game_button.setProperty("compact", True)
        self.launch_game_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout.addWidget(self.launch_game_button)

        self.play_demo_button = QPushButton(self._ui("play_demo"))
        self.play_demo_button.setObjectName("SecondaryButton")
        self.play_demo_button.setProperty("compact", True)
        self.play_demo_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout.addWidget(self.play_demo_button)
        layout.addStretch(1)

        self.game_auto_note_label = QLabel(self._ui("game_auto_note"))
        self.game_auto_note_label.setObjectName("SupportText")
        self.game_auto_note_label.setWordWrap(True)
        layout.addWidget(self.game_auto_note_label)

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
        signal_height = self.signal_area_widget.height() if hasattr(self, "signal_area_widget") else self.height()
        metric_width = max(1, signal_width)
        if metric_width >= 1180:
            metric_columns = 4
        elif metric_width >= 640:
            metric_columns = 2
        else:
            metric_columns = 1

        self._clear_layout(self.metric_grid)
        for index, card in enumerate(self.metric_card_widgets):
            row = index // metric_columns
            column = index % metric_columns
            self.metric_grid.addWidget(card, row, column)

        plot_width = max(1, signal_width)
        plot_columns = 2 if plot_width >= 760 else 1
        self._clear_layout(self.plot_grid)
        for index, card in enumerate(self.eeg_plot_widgets):
            row = index // plot_columns
            column = index % plot_columns
            self.plot_grid.addWidget(card, row, column)

        if self.ppg_plot_card is not None:
            ppg_row = (len(self.eeg_plot_widgets) + plot_columns - 1) // plot_columns
            self.plot_grid.addWidget(self.ppg_plot_card, ppg_row, 0, 1, plot_columns)

        metric_rows = (len(self.metric_card_widgets) + metric_columns - 1) // metric_columns
        plot_rows = (len(self.eeg_plot_widgets) + plot_columns - 1) // plot_columns
        if self.ppg_plot_card is not None:
            plot_rows += 1
        plot_card_height = self._clamp_int(
            (
                max(260, signal_height)
                - metric_rows * self._clamp_int(82 * self._responsive_scale(), 76, 112)
            )
            / max(plot_rows, 1)
            - 12,
            84,
            220,
        )
        for card in self.plot_cards:
            card.setMinimumHeight(plot_card_height)

        for row in range(self.plot_grid.rowCount()):
            self.plot_grid.setRowStretch(row, 1)
        for col in range(self.plot_grid.columnCount()):
            self.plot_grid.setColumnStretch(col, 1)

    def _relayout_experiment_tab(self) -> None:
        if not hasattr(self, "experiment_cards_grid"):
            return
        self._clear_layout(self.experiment_cards_grid)
        for column in range(3):
            self.experiment_cards_grid.setColumnStretch(column, 0)
        self.experiment_cards_grid.setRowStretch(0, 0)

        cards = (
            self.game_card_widget,
            self.examiner_card_widget,
            self.planner_card_widget,
        )
        for column, card in enumerate(cards):
            self.experiment_cards_grid.addWidget(card, 0, column)
            self.experiment_cards_grid.setColumnStretch(column, 1)
        self.experiment_cards_grid.setRowStretch(0, 1)

        self._relayout_examiner_form()
        self._relayout_planner_card()

    def _relayout_examiner_form(self) -> None:
        if not hasattr(self, "examiner_form_grid"):
            return

        examiner_width = self.examiner_card_widget.width() if hasattr(self, "examiner_card_widget") else self.width()
        compact_form = examiner_width < 320

        self._clear_layout(self.examiner_form_grid)
        row = 0
        for _field_key, label, widget in self.examiner_form_rows:
            if compact_form:
                self.examiner_form_grid.addWidget(label, row, 0, 1, 2)
                self.examiner_form_grid.addWidget(widget, row + 1, 0, 1, 2)
                row += 2
            else:
                self.examiner_form_grid.addWidget(label, row, 0)
                self.examiner_form_grid.addWidget(widget, row, 1)
                row += 1

        self.examiner_form_grid.setColumnStretch(0, 0 if compact_form else 1)
        self.examiner_form_grid.setColumnStretch(1, 0 if compact_form else 4)

    def _relayout_planner_card(self) -> None:
        if not hasattr(self, "relax_music_row"):
            return

        planner_width = self.planner_card_widget.width() if hasattr(self, "planner_card_widget") else self.width()
        compact_planner = planner_width < 350
        direction = QBoxLayout.Direction.TopToBottom if compact_planner else QBoxLayout.Direction.LeftToRight
        self.relax_music_row.setDirection(direction)
        self.relax_music_row.setSpacing(6 if compact_planner else 8)
        self.relax_music_row.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)

    def _build_log_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("SidebarCard")
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(26, 24, 26, 24)
        layout.setSpacing(12)

        self.log_card_title = QLabel(self._ui("session_log"))
        self.log_card_title.setObjectName("SectionTitle")
        self.log_output = QPlainTextEdit()
        self.log_output.setObjectName("LogOutput")
        self.log_output.setReadOnly(True)
        self.log_output.setPlaceholderText(self._ui("session_log_placeholder"))
        self.log_output.setMinimumHeight(56)
        self.log_output.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(self.log_card_title)
        layout.addWidget(self.log_output, stretch=1)
        return card

    def _build_examiner_details_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("SidebarCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(8)

        self.examiner_card_title = QLabel(self._ui("examiner_control"))
        self.examiner_card_title.setObjectName("SectionTitle")
        layout.addWidget(self.examiner_card_title)

        self.examiner_subtitle_label = QLabel()
        self.examiner_subtitle_label.setObjectName("ExaminerBody")
        self.examiner_subtitle_label.setWordWrap(True)
        layout.addWidget(self.examiner_subtitle_label)

        form_grid = QGridLayout()
        self.examiner_form_grid = form_grid
        form_grid.setHorizontalSpacing(6)
        form_grid.setVerticalSpacing(6)

        self.examiner_name_input = QLineEdit()
        self.examiner_name_input.setProperty("compact", True)
        self.examiner_id_input = QLineEdit()
        self.examiner_id_input.setProperty("compact", True)
        self.examiner_device_id_input = QLineEdit()
        self.examiner_device_id_input.setProperty("compact", True)
        self.examiner_age_input = QLineEdit()
        self.examiner_age_input.setProperty("compact", True)
        self.examiner_n_value_input = QLineEdit("2")
        self.examiner_n_value_input.setProperty("compact", True)
        self.examiner_n_value_input.setMaximumWidth(120)
        self.examiner_note_input = QTextEdit()
        self.examiner_note_input.setProperty("compact", True)
        self.examiner_note_input.setMinimumHeight(72)

        self.examiner_field_labels: dict[str, QLabel] = {}
        self.examiner_form_rows: list[tuple[str, QLabel, QWidget]] = []
        primary_fields = [
            ("name", self.examiner_name_input),
            ("id", self.examiner_id_input),
            ("device_id", self.examiner_device_id_input),
            ("age", self.examiner_age_input),
            ("n_value", self.examiner_n_value_input),
        ]
        for row, (field_key, widget) in enumerate(primary_fields):
            label = QLabel(self._ui(f"field_{field_key}"))
            label.setObjectName("FieldLabel")
            self.examiner_field_labels[field_key] = label
            self.examiner_form_rows.append((field_key, label, widget))
        note_row = len(primary_fields) + 1
        note_label = QLabel(self._ui("field_note"))
        note_label.setObjectName("FieldLabel")
        self.examiner_field_labels["note"] = note_label
        self.examiner_form_rows.append(("note", note_label, self.examiner_note_input))
        form_grid.setColumnStretch(1, 1)
        layout.addLayout(form_grid)

        layout.addStretch(1)
        self._relayout_examiner_form()
        return card

    def _build_session_planner_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("SidebarCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(12)

        self.planner_title_label = QLabel(self._ui("planner_title"))
        self.planner_title_label.setObjectName("SectionTitle")
        layout.addWidget(self.planner_title_label)

        audio_panel = QFrame()
        audio_panel.setObjectName("InsetPanel")
        audio_layout = QVBoxLayout(audio_panel)
        audio_layout.setContentsMargins(16, 14, 16, 14)
        audio_layout.setSpacing(10)
        audio_title = QLabel("Audio")
        audio_title.setObjectName("InsetTitle")
        audio_layout.addWidget(audio_title)

        relax_music_row = QHBoxLayout()
        self.relax_music_row = relax_music_row
        relax_music_row.setContentsMargins(0, 0, 0, 0)
        relax_music_row.setSpacing(8)
        self.relax_music_label = QLabel(self._ui("field_relax_audio"))
        self.relax_music_label.setObjectName("FieldLabel")
        relax_music_row.addWidget(self.relax_music_label, 1)
        switch_cluster = QHBoxLayout()
        self.relax_music_switch_cluster = switch_cluster
        switch_cluster.setContentsMargins(0, 0, 0, 0)
        switch_cluster.setSpacing(8)
        self.relax_music_switch = SlideSwitch()
        self.relax_music_switch.setChecked(False)
        self.relax_music_switch_label = QLabel(self._ui("music_switch_off"))
        self.relax_music_switch_label.setObjectName("RelaxMusicSwitchCaption")
        switch_cluster.addWidget(self.relax_music_switch, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        switch_cluster.addWidget(self.relax_music_switch_label, 0, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        relax_music_row.addLayout(switch_cluster)
        self.relax_music_switch.toggled.connect(self._update_relax_music_switch_text)
        self.relax_music_switch.toggled.connect(self._sync_music_track_enabled_state)
        audio_layout.addLayout(relax_music_row)

        self.music_track_label = QLabel(self._ui("field_music_track"))
        self.music_track_label.setObjectName("FieldLabel")
        audio_layout.addWidget(self.music_track_label)
        self.music_track_combo = QComboBox()
        self.music_track_combo.setProperty("compact", True)
        for track_id, label_key in self._RELAX_MUSIC_ITEMS:
            self.music_track_combo.addItem(self._ui(label_key), track_id)
        audio_layout.addWidget(self.music_track_combo)
        self._sync_music_track_enabled_state()

        self.announcement_volume_label = QLabel(self._ui("field_announcement_volume"))
        self.announcement_volume_label.setObjectName("FieldLabel")
        audio_layout.addWidget(self.announcement_volume_label)
        self.announcement_volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.announcement_volume_slider.setRange(0, 100)
        self.announcement_volume_slider.setValue(70)
        self.announcement_volume_slider.setSingleStep(5)
        self.announcement_volume_slider.setPageStep(10)
        audio_layout.addWidget(self.announcement_volume_slider)
        layout.addWidget(audio_panel)

        planner_panel = QFrame()
        planner_panel.setObjectName("InsetPanel")
        planner_layout = QVBoxLayout(planner_panel)
        planner_layout.setContentsMargins(16, 14, 16, 14)
        planner_layout.setSpacing(10)
        planner_section_title = QLabel("Session Flow")
        planner_section_title.setObjectName("InsetTitle")
        planner_layout.addWidget(planner_section_title)
        planner_grid = QGridLayout()
        planner_grid.setHorizontalSpacing(8)
        planner_grid.setVerticalSpacing(8)
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
            order_input.setProperty("compact", True)
            duration_input.setProperty("compact", True)
            order_input.setMaximumWidth(70)
            duration_input.setMaximumWidth(120)
            self.stage_order_inputs[stage_key] = order_input
            self.stage_duration_inputs[stage_key] = duration_input
            planner_grid.addWidget(order_input, row, 1)
            planner_grid.addWidget(duration_input, row, 2)
        planner_grid.setColumnStretch(2, 1)
        planner_layout.addLayout(planner_grid)

        self.examiner_help_label = QLabel()
        self.examiner_help_label.setObjectName("ExaminerBody")
        self.examiner_help_label.setWordWrap(True)
        planner_layout.addWidget(self.examiner_help_label)
        layout.addWidget(planner_panel)
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
        self.announcement_volume_slider.valueChanged.connect(self._on_announcement_volume_slider_changed)
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
            self._append_log(self._ui("connect_device_failed", error=error))
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
            self._append_log(self._ui("disconnect_device_failed", error=error))
            return
        if saved_files is None:
            self._append_log("Device disconnected.")

    def _toggle_recording(self) -> None:
        status = self.controller.status()
        if not status.running:
            self._append_log(self._ui("no_device_recording"))
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
        self._save_form_defaults(examiner_setup)

        status = self.controller.status()
        self.pending_game_auto_record = False
        if not status.running:
            self._append_log(self._ui("start_game_no_device"))

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
            self.plot_cards[index].canvas.update_series(
                display_values,
                self.config.max_points,
                auto_scale=False,
            )
        self.plot_cards[-1].canvas.update_series(
            ppg_series,
            self.config.max_points,
            auto_scale=False,
            min_half_range=18.0,
        )

        bpm = hr_series[-1] if hr_series else estimate_hr_from_ppg(ppg_series, self.config.ppg_sampling_rate)
        battery = self.controller.battery_percent or self.device_manager.current_battery_percent
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
        elif game.supported_languages:
            self.game_language_combo.setCurrentIndex(0)
        self.game_language_combo.blockSignals(False)
        self.game_description_label.setText("")
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
            self._append_log(self._ui("n_value_required"))
            return None
        try:
            n_value = int(n_value_text)
        except ValueError:
            self._append_log(self._ui("n_value_integer"))
            return None
        if n_value < 1:
            self._append_log(self._ui("n_value_positive"))
            return None
        return n_value

    def _load_form_defaults(self) -> None:
        path = self.project_root / "form_defaults.json"
        if not path.exists():
            return
        try:
            with open(path) as f:
                d = json.load(f)
        except Exception:
            return
        self.examiner_name_input.setText(str(d.get("participant_name", "")))
        self.examiner_id_input.setText(str(d.get("participant_id", "")))
        self.examiner_device_id_input.setText(str(d.get("device_id", "")))
        self.examiner_age_input.setText(str(d.get("age", "")))
        self.examiner_n_value_input.setText(str(d.get("n_value", "2")))
        self.examiner_note_input.setPlainText(str(d.get("note", "")))
        for stage_key in ("relax", "break", "game"):
            if order := str(d.get(f"stage_{stage_key}_order", "")):
                self.stage_order_inputs[stage_key].setText(order)
            if duration := str(d.get(f"stage_{stage_key}_duration", "")):
                self.stage_duration_inputs[stage_key].setText(duration)
        if "relax_audio_enabled" in d:
            self.relax_music_switch.setChecked(bool(d["relax_audio_enabled"]))
        if track := str(d.get("relax_music_track", "")):
            idx = self.music_track_combo.findData(track)
            if idx >= 0:
                self.music_track_combo.setCurrentIndex(idx)
        if "announcement_volume" in d:
            self.announcement_volume_slider.setValue(int(d["announcement_volume"]))

    def _save_form_defaults(self, examiner_setup: dict[str, object]) -> None:
        path = self.project_root / "form_defaults.json"
        defaults: dict[str, object] = {
            "participant_name": str(examiner_setup.get("participant_name", "")),
            "participant_id": str(examiner_setup.get("participant_id", "")),
            "device_id": str(examiner_setup.get("device_id", "")),
            "age": str(examiner_setup.get("age", "")),
            "n_value": str(examiner_setup.get("n_value", "2")),
            "note": str(examiner_setup.get("note", "")),
            "relax_audio_enabled": bool(examiner_setup.get("relax_audio_enabled", False)),
            "relax_music_track": str(examiner_setup.get("relax_music_track", "binaural_sound")),
            "announcement_volume": int(self.announcement_volume_slider.value()),
        }
        for stage in examiner_setup.get("session_stages", []):
            if isinstance(stage, dict):
                key = stage.get("kind", "")
                defaults[f"stage_{key}_order"] = str(stage.get("order", ""))
                defaults[f"stage_{key}_duration"] = str(stage.get("duration_minutes", ""))
        try:
            with open(path, "w") as f:
                json.dump(defaults, f, indent=2)
        except Exception:
            pass

    def _collect_examiner_setup(self) -> dict[str, object] | None:
        participant_name = self.examiner_name_input.text().strip()
        participant_id = self.examiner_id_input.text().strip()
        device_id = self.examiner_device_id_input.text().strip()
        age = self.examiner_age_input.text().strip()
        n_value_text = self.examiner_n_value_input.text().strip()
        relax_audio_enabled = self.relax_music_switch.isChecked()
        relax_music_track = str(self.music_track_combo.currentData() or "binaural_sound")
        announcement_volume = float(self.announcement_volume_slider.value()) / 100.0
        note = self.examiner_note_input.toPlainText().strip()

        if not participant_name:
            self._append_log(self._ui("name_required"))
            return None
        if not participant_id:
            self._append_log(self._ui("id_required"))
            return None
        if not participant_id.isdigit():
            self._append_log("ID must contain numbers only. Prefix P is added automatically.")
            return None
        if not device_id:
            self._append_log(self._ui("device_id_required"))
            return None
        if not age:
            self._append_log(self._ui("age_required"))
            return None
        if not n_value_text:
            self._append_log(self._ui("n_value_required"))
            return None
        try:
            n_value = int(n_value_text)
        except ValueError:
            self._append_log(self._ui("n_value_integer"))
            return None
        if n_value < 1:
            self._append_log(self._ui("n_value_positive"))
            return None

        stage_plan: list[dict[str, object]] = []
        orders: list[int] = []
        for stage_key in ("relax", "break", "game"):
            order_text = self.stage_order_inputs[stage_key].text().strip()
            duration_text = self.stage_duration_inputs[stage_key].text().strip()
            try:
                order = int(order_text)
            except ValueError:
                self._append_log(self._ui("order_whole_number", stage=self._stage_label(stage_key)))
                return None
            try:
                duration = float(duration_text)
            except ValueError:
                self._append_log(self._ui("duration_number", stage=self._stage_label(stage_key)))
                return None
            if order not in (1, 2, 3):
                self._append_log(self._ui("order_range", stage=self._stage_label(stage_key)))
                return None
            if duration < 0:
                self._append_log(self._ui("duration_negative", stage=self._stage_label(stage_key)))
                return None
            orders.append(order)
            stage_plan.append({"kind": stage_key, "order": order, "duration_minutes": duration})

        if sorted(orders) != [1, 2, 3]:
            self._append_log(self._ui("order_unique"))
            return None
        game_stage = next(stage for stage in stage_plan if stage["kind"] == "game")
        if float(game_stage["duration_minutes"]) <= 0:
            self._append_log(self._ui("game_duration_positive"))
            return None

        return {
            "participant_name": participant_name,
            "participant_id": participant_id,
            "device_id": device_id,
            "age": age,
            "n_value": n_value,
            "relax_audio_enabled": relax_audio_enabled,
            "relax_music_track": relax_music_track,
            "announcement_volume": announcement_volume,
            "note": note,
            "session_stages": stage_plan,
        }

    def _update_relax_music_switch_text(self, _checked: bool | None = None) -> None:
        if not hasattr(self, "relax_music_switch_label"):
            return
        key = "music_switch_on" if self.relax_music_switch.isChecked() else "music_switch_off"
        self.relax_music_switch_label.setText(self._ui(key))

    def _sync_music_track_enabled_state(self, _checked: bool | None = None) -> None:
        if hasattr(self, "music_track_combo"):
            self.music_track_combo.setEnabled(True)

    def _refresh_music_track_combo_labels(self) -> None:
        if not hasattr(self, "music_track_combo"):
            return
        current_track = str(self.music_track_combo.currentData() or "binaural_sound")
        for index, (_track_id, label_key) in enumerate(self._RELAX_MUSIC_ITEMS):
            if index < self.music_track_combo.count():
                self.music_track_combo.setItemText(index, self._ui(label_key))
        idx = self.music_track_combo.findData(current_track)
        if idx >= 0:
            self.music_track_combo.setCurrentIndex(idx)

    @staticmethod
    def _resolve_preview_sound_path() -> Path | None:
        candidates = (
            Path("/System/Library/Sounds/Pong.aiff"),
            Path("/System/Library/Sounds/Ping.aiff"),
        )
        for candidate in candidates:
            if candidate.exists():
                return candidate
        return None

    def _on_announcement_volume_slider_changed(self, _value: int) -> None:
        self.announcement_preview_timer.start(140)

    def _play_announcement_preview_sound(self) -> None:
        volume = max(0.0, min(float(self.announcement_volume_slider.value()) / 100.0, 1.0))
        if self.afplay_command is None or self.preview_sound_path is None:
            QApplication.beep()
            return

        command = [self.afplay_command, "-v", f"{volume:.2f}", str(self.preview_sound_path)]

        def run_preview() -> None:
            try:
                subprocess.run(command, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                pass

        threading.Thread(target=run_preview, daemon=True).start()

    def _append_log(self, message: str) -> None:
        stamp = datetime.now().strftime("%H:%M:%S")
        self.log_output.appendPlainText(f"[{stamp}] {message}")
        if message.startswith("Saved to "):
            self.last_saved_text = message.removeprefix("Saved to ")

    def _current_save_context(self) -> dict[str, str]:
        return self._save_context_from_examiner_setup(
            {
                "participant_id": self.examiner_id_input.text().strip(),
                "device_id": self.examiner_device_id_input.text().strip(),
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
        device_id = str(examiner_setup.get("device_id", "")).strip() or "unknown_device"
        session_stages = examiner_setup.get("session_stages", [])
        session_label = ModernMuseWindow._session_label_from_stages(session_stages)
        return {"user_id": participant_id, "device_id": device_id, "session_label": session_label}

    @staticmethod
    def _session_label_from_stages(session_stages: object) -> str:
        mapping = {"relax": "A", "break": "B", "game": "C"}
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
        scale = self._responsive_scale()
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
                border-radius: {self._clamp_int(14 * scale, 12, 18)}px;
                padding: {self._clamp_int(9 * scale, 8, 12)}px {self._clamp_int(12 * scale, 10, 16)}px;
                font-size: {self._clamp_int(12 * scale, 11, 14)}px;
                font-weight: 700;
            }}
            """
        )

    def _set_badge_style(self, label: QLabel, *, active: bool, accent: str) -> None:
        scale = self._responsive_scale()
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
                border-radius: {self._clamp_int(18 * scale, 14, 22)}px;
                padding: {self._clamp_int(9 * scale, 8, 12)}px {self._clamp_int(17 * scale, 14, 22)}px;
                font-size: {self._clamp_int(13 * scale, 11, 15)}px;
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
        self._apply_responsive_layout()
