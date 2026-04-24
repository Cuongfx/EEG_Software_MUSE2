from __future__ import annotations

import argparse
import ast
import csv
import json
import math
import mimetypes
import os
import re
import tempfile
import threading
import time
import webbrowser
from collections import deque
from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

_mpl_cache_dir = Path(tempfile.gettempdir()) / "eeg_analyse_mpl"
_mpl_cache_dir.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(_mpl_cache_dir))
_xdg_cache_dir = Path(tempfile.gettempdir()) / "eeg_analyse_cache"
_xdg_cache_dir.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("XDG_CACHE_HOME", str(_xdg_cache_dir))

from GAME import GameRegistry
from GAME.n_back.config import calculate_trial_count, load_rules
from GAME.n_back.master_control import append_master_control_row, ensure_master_control_workbook

PROJECT_ROOT = Path(__file__).resolve().parents[1]
STATIC_ROOT = Path(__file__).resolve().parent / "static"
EEG_IMPORT_ERROR: Exception | None = None
CONSENT_IMPORT_ERROR: Exception | None = None

def _load_legacy_game_constant(name: str, fallback: Any) -> Any:
    try:
        tree = ast.parse((PROJECT_ROOT / "GAME" / "n_back" / "game.py").read_text())
        for node in tree.body:
            if not isinstance(node, ast.Assign):
                continue
            if any(isinstance(target, ast.Name) and target.id == name for target in node.targets):
                return ast.literal_eval(node.value)
    except Exception as exc:  # pragma: no cover - fallback only.
        global CONSENT_IMPORT_ERROR
        CONSENT_IMPORT_ERROR = exc
    return fallback


CONSENT_TEXT = _load_legacy_game_constant(
    "CONSENT_TEXT",
    {
        "en": (
            "EEG Study Participation - Terms, Conditions, and Informed Consent\n\n"
            "Participation is voluntary. EEG recording is non-invasive and may involve "
            "minor temporary discomfort from sensors. The study may collect EEG signals "
            "and age for academic research. Direct identifiers should not be published. "
            "You may withdraw before anonymized data is released. By continuing, you "
            "confirm that you understand the study and agree to participate."
        )
    },
)
GAME_TRANSLATIONS = _load_legacy_game_constant("TRANSLATIONS", {"en": {}})

try:
    from EEG_APP import (
        AppConfig,
        MuseDevice,
        MuseDeviceManager,
        MuseStreamController,
        SessionState,
        SignalProcessor,
    )
    from EEG_APP.processing import estimate_hr_from_ppg
except Exception as exc:  # pragma: no cover - exercised only when dependencies are absent.
    EEG_IMPORT_ERROR = exc

    @dataclass(frozen=True)
    class EEGChannelConfig:
        index: int
        name: str
        dead: bool = False

    @dataclass(frozen=True)
    class AppConfig:
        max_points: int = 1000
        eeg_sampling_rate: int = 256
        ppg_sampling_rate: int = 64
        stream_timeout: int = 10
        stream_name: str = "Muse"
        result_dir: str = "EEG_APP/results"
        plot_update_interval_ms: int = 80
        device_warmup_seconds: float = 2.5
        muselsl_retries: int = 9999
        muselsl_restart_delay_seconds: float = 2.0
        stream_recovery_cooldown_seconds: float = 1.5
        eeg_plot_range_uv: tuple[float, float] = (-200.0, 200.0)
        ppg_plot_range: tuple[float, float] = (-200.0, 200.0)
        eeg_file_prefix: str = "eeg_data"
        ppg_file_prefix: str = "ppg_data"
        eeg_channels: tuple[EEGChannelConfig, ...] = field(
            default_factory=lambda: (
                EEGChannelConfig(index=0, name="TP9"),
                EEGChannelConfig(index=1, name="AF7"),
                EEGChannelConfig(index=2, name="AF8"),
                EEGChannelConfig(index=3, name="TP10"),
            )
        )

        @property
        def eeg_channel_count(self) -> int:
            return len(self.eeg_channels)

    @dataclass(frozen=True)
    class MuseDevice:
        name: str
        address: str
        rssi: int | None = None

        @property
        def display_name(self) -> str:
            if self.rssi is None:
                return f"{self.name} ({self.address})"
            return f"{self.name} ({self.address}, RSSI {self.rssi})"

    @dataclass(frozen=True)
    class ControllerStatus:
        running: bool
        eeg_samples: int
        ppg_samples: int
        eeg_connected: bool
        ppg_connected: bool
        recording: bool

    class SessionState:
        def __init__(self, config: AppConfig) -> None:
            self.config = config
            self.data_lock = threading.Lock()
            self.eeg_raw_buffers = [deque(maxlen=config.max_points) for _ in range(config.eeg_channel_count)]
            self.ppg_filtered_buffer = deque(maxlen=config.max_points)
            self.heart_rate_buffer = deque(maxlen=config.max_points)
            self.recording_enabled = False

    class SignalProcessor:
        def __init__(self, _config: AppConfig, _state: SessionState) -> None:
            pass

    class MuseStreamController:
        def __init__(self, _config: AppConfig, state: SessionState, _processor: SignalProcessor, status_sink=None) -> None:
            self.state = state
            self.status_sink = status_sink or (lambda message: None)
            self.running = False
            self.eeg_inlet = None
            self.ppg_inlet = None
            self.battery_percent = None

        def start(self) -> None:
            raise RuntimeError(f"EEG dependencies are unavailable: {EEG_IMPORT_ERROR}")

        def stop(self, save: bool = True):
            del save
            self.running = False
            self.state.recording_enabled = False
            return None

        def start_recording(self) -> None:
            raise RuntimeError(f"EEG dependencies are unavailable: {EEG_IMPORT_ERROR}")

        def stop_recording(self, save: bool = True):
            del save
            self.state.recording_enabled = False
            return None

        def set_save_context(self, *, user_id: str, device_id: str, session_label: str) -> None:
            del user_id, device_id, session_label

        def status(self) -> ControllerStatus:
            return ControllerStatus(False, 0, 0, False, False, self.state.recording_enabled)

    class MuseDeviceManager:
        def __init__(self, log_sink=None, **_kwargs) -> None:
            self.log_sink = log_sink or (lambda message: None)
            self.current_device = None
            self.current_battery_percent = None

        def scan_devices(self) -> list[MuseDevice]:
            self.log_sink(f"Device scan unavailable because EEG dependencies are missing: {EEG_IMPORT_ERROR}")
            return []

        def read_battery_percentage(self, _device: MuseDevice) -> None:
            return None

        def connect(self, _device: MuseDevice, *, include_ppg: bool = True) -> None:
            del include_ppg
            raise RuntimeError(f"EEG dependencies are unavailable: {EEG_IMPORT_ERROR}")

        def disconnect(self) -> None:
            self.current_device = None

        def is_connected(self) -> bool:
            return False

    def estimate_hr_from_ppg(_ppg_filtered: list[float], _fs: int) -> float | None:
        return None

def _now_stamp() -> str:
    return datetime.now().strftime("%H:%M:%S")


def _safe_token(value: str, *, fallback: str = "participant") -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "_", str(value).strip())
    return cleaned or fallback


def _participant_file_id(value: str) -> str:
    raw = str(value).strip()
    if raw.upper().startswith("P"):
        raw = raw[1:]
    digits = re.sub(r"[^0-9]+", "", raw)
    return f"P{digits}" if digits else "Punknown"


def _session_label_from_stages(session_stages: object) -> str:
    mapping = {"relax": "A", "break": "B", "game": "C"}
    ordered: list[tuple[int, str]] = []
    if isinstance(session_stages, list):
        for stage in session_stages:
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


def _round_series(values: list[float], *, digits: int = 3) -> list[float | None]:
    rounded: list[float | None] = []
    for value in values:
        number = float(value)
        rounded.append(round(number, digits) if math.isfinite(number) else None)
    return rounded


class EEGWebApplication:
    def __init__(self) -> None:
        self.config = AppConfig()
        self.state = SessionState(self.config)
        self.processor = SignalProcessor(self.config, self.state)
        self.controller = MuseStreamController(
            self.config,
            self.state,
            self.processor,
            status_sink=self.log,
        )
        self.device_manager = MuseDeviceManager(
            log_sink=self.log,
            muselsl_retries=self.config.muselsl_retries,
            restart_delay_seconds=self.config.muselsl_restart_delay_seconds,
        )
        self.game_registry = GameRegistry(PROJECT_ROOT)
        self.rules = load_rules(PROJECT_ROOT / "GAME" / "n_back" / "rules.txt")
        self.form_defaults_path = PROJECT_ROOT / "form_defaults.json"
        self.logs: deque[str] = deque(maxlen=500)
        self.operation_lock = threading.Lock()
        self.connection_busy = False
        self.last_saved_text = "No recording saved yet"
        self.log("Web application ready.")
        if EEG_IMPORT_ERROR is not None:
            self.log(f"EEG hardware controls are unavailable until dependencies are installed: {EEG_IMPORT_ERROR}")
        if CONSENT_IMPORT_ERROR is not None:
            self.log(f"Using built-in web consent text because legacy game text could not be loaded: {CONSENT_IMPORT_ERROR}")

    def log(self, message: str) -> None:
        line = f"[{_now_stamp()}] {message}"
        self.logs.append(line)
        if message.startswith("Saved to "):
            self.last_saved_text = message.removeprefix("Saved to ")

    def config_payload(self) -> dict[str, Any]:
        games = []
        for game in self.game_registry.list_games():
            games.append(
                {
                    "game_id": game.game_id,
                    "title": game.title,
                    "description": game.description,
                    "supported_languages": list(game.supported_languages),
                    "source": game.source,
                }
            )
        return {
            "app": {
                "name": "EEG Analyse",
                "mode": "web",
                "hardwareAvailable": EEG_IMPORT_ERROR is None,
                "dependencyError": str(EEG_IMPORT_ERROR) if EEG_IMPORT_ERROR is not None else None,
                "legacyTextLoadError": str(CONSENT_IMPORT_ERROR) if CONSENT_IMPORT_ERROR is not None else None,
            },
            "channels": [asdict(channel) for channel in self.config.eeg_channels],
            "maxPoints": self.config.max_points,
            "plotRanges": {
                "eeg": list(self.config.eeg_plot_range_uv),
                "ppg": list(self.config.ppg_plot_range),
            },
            "rules": asdict(self.rules),
            "trialCountDefault": calculate_trial_count(
                self.rules.actual_minutes,
                self.rules.display_time_ms,
                self.rules.intertrial_interval_ms,
            ),
            "games": games,
            "languageLabels": {
                "en": "English",
                "de": "German",
                "vi": "Vietnamese",
                "zh": "Chinese",
                "ar": "Arabic",
                "ko": "Korean",
                "ja": "Japanese",
                "fr": "French",
                "es": "Spanish",
                "ru": "Russian",
                "it": "Italian",
                "pt": "Portuguese",
            },
            "consentText": CONSENT_TEXT,
            "gameText": GAME_TRANSLATIONS,
            "defaults": self.load_defaults(),
            "media": {
                "binaural_sound": "/media/alpha_15m.mp3",
                "rain_sound": "/media/rain_sound_15m.mp3",
            },
        }

    def status_payload(self) -> dict[str, Any]:
        status = self.controller.status()
        with self.state.data_lock:
            eeg_series = [list(buffer) for buffer in self.state.eeg_raw_buffers]
            ppg_series = list(self.state.ppg_filtered_buffer)
            hr_series = list(self.state.heart_rate_buffer)

        bpm = hr_series[-1] if hr_series else estimate_hr_from_ppg(ppg_series, self.config.ppg_sampling_rate)
        battery = self.controller.battery_percent or self.device_manager.current_battery_percent
        current_device = self.device_manager.current_device
        return {
            "running": status.running,
            "recording": status.recording,
            "eegConnected": status.eeg_connected,
            "ppgConnected": status.ppg_connected,
            "eegSamples": status.eeg_samples,
            "ppgSamples": status.ppg_samples,
            "connectionBusy": self.connection_busy,
            "batteryPercent": round(float(battery), 1) if battery is not None else None,
            "heartRateBpm": round(float(bpm), 1) if bpm is not None else None,
            "currentDevice": asdict(current_device) if current_device is not None else None,
            "lastSaved": self.last_saved_text,
            "series": {
                "eeg": [_round_series(values) for values in eeg_series],
                "ppg": _round_series(ppg_series),
            },
            "logs": list(self.logs)[-160:],
        }

    def scan_devices(self) -> dict[str, Any]:
        devices = self.device_manager.scan_devices()
        self.log(f"Device scan completed. Found {len(devices)} device(s).")
        return {"devices": [asdict(device) | {"display_name": device.display_name} for device in devices]}

    def connect_device(self, payload: dict[str, Any]) -> dict[str, Any]:
        device = MuseDevice(
            name=str(payload.get("name", "Muse")),
            address=str(payload.get("address", "")),
            rssi=payload.get("rssi"),
        )
        with self.operation_lock:
            if self.connection_busy:
                raise WebError(HTTPStatus.CONFLICT, "A connection operation is already running.")
            self.connection_busy = True
        try:
            self.log(f"Connecting to {device.display_name}...")
            self._disconnect_internal(save_recording=True)
            self.device_manager.read_battery_percentage(device)
            self.device_manager.connect(device, include_ppg=True)
            time.sleep(self.config.device_warmup_seconds)
            self.controller.start()
            self.log(f"Connected to {device.display_name}")
            return {"ok": True, "device": asdict(device) | {"display_name": device.display_name}}
        except Exception as exc:
            self.device_manager.disconnect()
            self.log(f"Could not connect to the selected device: {exc}")
            raise WebError(HTTPStatus.INTERNAL_SERVER_ERROR, str(exc)) from exc
        finally:
            self.connection_busy = False

    def disconnect_device(self, *, save_recording: bool = True) -> dict[str, Any]:
        with self.operation_lock:
            if self.connection_busy:
                raise WebError(HTTPStatus.CONFLICT, "A connection operation is already running.")
            self.connection_busy = True
        try:
            saved_files = self._disconnect_internal(save_recording=save_recording)
            self.log("Device disconnected.")
            return {"ok": True, "savedFiles": self._saved_files_payload(saved_files)}
        finally:
            self.connection_busy = False

    def start_recording(self, payload: dict[str, Any]) -> dict[str, Any]:
        status = self.controller.status()
        if not status.running:
            raise WebError(HTTPStatus.CONFLICT, "Connect a device before recording.")
        context = self.save_context_from_setup(payload.get("examinerSetup") or payload)
        self.controller.set_save_context(**context)
        if not status.recording:
            self.controller.start_recording()
        return {"ok": True, "context": context}

    def stop_recording(self, *, save: bool = True) -> dict[str, Any]:
        status = self.controller.status()
        if not status.recording:
            return {"ok": True, "savedFiles": None, "message": "Recording was not active."}
        saved_files = self.controller.stop_recording(save=save)
        return {"ok": True, "savedFiles": self._saved_files_payload(saved_files)}

    def load_defaults(self) -> dict[str, Any]:
        if not self.form_defaults_path.exists():
            return {}
        try:
            return json.loads(self.form_defaults_path.read_text())
        except Exception:
            return {}

    def save_defaults(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.form_defaults_path.write_text(json.dumps(payload, indent=2, sort_keys=True))
        self.log("Saved web form defaults.")
        return {"ok": True, "defaults": payload}

    def save_game_result(self, payload: dict[str, Any]) -> dict[str, Any]:
        session = payload.get("session")
        trials = payload.get("trials")
        if not isinstance(session, dict):
            raise WebError(HTTPStatus.BAD_REQUEST, "Missing session details.")
        if not isinstance(trials, list):
            raise WebError(HTTPStatus.BAD_REQUEST, "Missing trial results.")

        result_folder = PROJECT_ROOT / "GAME" / "n_back" / "result"
        result_folder.mkdir(parents=True, exist_ok=True)
        date_token = datetime.now().strftime("%Y-%m-%d")
        arrangement_token = _session_label_from_stages(session.get("session_stages"))
        participant_id = str(session.get("participant_id", "")).strip()
        file_token = _safe_token(participant_id)
        output_file = result_folder / f"{file_token}_{date_token}_{arrangement_token}.csv"

        with output_file.open("w", newline="") as file:
            writer = csv.DictWriter(
                file,
                fieldnames=[
                    "participantName",
                    "participantId",
                    "age",
                    "dateExperimentStart",
                    "timeExperimentStart",
                    "blockNumber",
                    "nValue",
                    "trialNumber",
                    "letter",
                    "matchOrNotMatch",
                    "timestampLetterAppeared",
                    "timestampLetterDisappeared",
                    "isKeyPressed",
                    "note",
                    "sessionArrangement",
                ],
            )
            writer.writeheader()
            for index, trial in enumerate(trials, start=1):
                if not isinstance(trial, dict):
                    continue
                writer.writerow(
                    {
                        "participantName": session.get("participant_name", ""),
                        "participantId": participant_id,
                        "age": session.get("age", ""),
                        "dateExperimentStart": payload.get("dateExperimentStart", date.today().strftime("%d/%m/%Y")),
                        "timeExperimentStart": payload.get("timeExperimentStart", ""),
                        "blockNumber": trial.get("blockNumber", 1),
                        "nValue": session.get("n_value", ""),
                        "trialNumber": trial.get("trialNumber", index),
                        "letter": trial.get("letter", ""),
                        "matchOrNotMatch": trial.get("matchOrNotMatch", ""),
                        "timestampLetterAppeared": trial.get("timestampLetterAppeared", ""),
                        "timestampLetterDisappeared": trial.get("timestampLetterDisappeared", ""),
                        "isKeyPressed": trial.get("isKeyPressed", ""),
                        "note": session.get("note", ""),
                        "sessionArrangement": arrangement_token,
                    }
                )

        master_control_path = result_folder / "Master_Control.xlsx"
        ensure_master_control_workbook(master_control_path)
        score = float(payload.get("score", 0.0) or 0.0)
        append_master_control_row(
            master_control_path,
            [
                str(session.get("participant_name", "")),
                participant_id,
                str(session.get("age", "")),
                str(session.get("n_value", "")),
                "yes" if bool(session.get("relax_audio_enabled", False)) else "",
                f"{score:.2f}",
                str(session.get("note", "")),
                "yes" if bool(payload.get("consentAccepted", False)) else "",
            ],
        )
        self.log(f"Saved Focus Game result to {output_file}")
        return {"ok": True, "resultPath": str(output_file), "score": round(score, 2)}

    def save_context_from_setup(self, setup: object) -> dict[str, str]:
        if not isinstance(setup, dict):
            setup = {}
        participant_id = str(setup.get("participant_id", "")).strip() or "unknown"
        device_id = str(setup.get("device_id", "")).strip() or "unknown_device"
        session_label = _session_label_from_stages(setup.get("session_stages"))
        return {
            "user_id": participant_id,
            "device_id": device_id,
            "session_label": session_label,
        }

    def _disconnect_internal(self, *, save_recording: bool):
        saved_files = None
        if self.state.recording_enabled:
            saved_files = self.controller.stop_recording(save=save_recording)
        if self.controller.running or self.controller.eeg_inlet is not None or self.controller.ppg_inlet is not None:
            self.controller.stop(save=False)
        self.device_manager.disconnect()
        return saved_files

    @staticmethod
    def _saved_files_payload(saved_files) -> dict[str, str | None] | None:
        if saved_files is None:
            return None
        return {
            "eegPath": str(saved_files.eeg_path),
            "ppgPath": str(saved_files.ppg_path) if saved_files.ppg_path is not None else None,
        }


class WebError(Exception):
    def __init__(self, status: HTTPStatus, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.message = message


class EEGRequestHandler(BaseHTTPRequestHandler):
    server_version = "EEGWeb/1.0"

    @property
    def app(self) -> EEGWebApplication:
        return self.server.app  # type: ignore[attr-defined]

    def do_GET(self) -> None:  # noqa: N802
        try:
            self._route_get(send_body=True)
        except WebError as exc:
            self._send_error(exc.status, exc.message)
        except Exception as exc:
            self.app.log(f"Request failed: {exc}")
            self._send_error(HTTPStatus.INTERNAL_SERVER_ERROR, str(exc))

    def do_HEAD(self) -> None:  # noqa: N802
        try:
            self._route_get(send_body=False)
        except WebError as exc:
            self._send_error(exc.status, exc.message)
        except Exception as exc:
            self.app.log(f"Request failed: {exc}")
            self._send_error(HTTPStatus.INTERNAL_SERVER_ERROR, str(exc))

    def do_POST(self) -> None:  # noqa: N802
        try:
            parsed = urlparse(self.path)
            payload = self._read_json()
            if parsed.path == "/api/device/connect":
                self._send_json(self.app.connect_device(payload))
            elif parsed.path == "/api/device/disconnect":
                self._send_json(self.app.disconnect_device(save_recording=bool(payload.get("saveRecording", True))))
            elif parsed.path == "/api/recording/start":
                self._send_json(self.app.start_recording(payload))
            elif parsed.path == "/api/recording/stop":
                self._send_json(self.app.stop_recording(save=bool(payload.get("save", True))))
            elif parsed.path == "/api/defaults":
                self._send_json(self.app.save_defaults(payload))
            elif parsed.path == "/api/game-results":
                self._send_json(self.app.save_game_result(payload))
            else:
                self._send_error(HTTPStatus.NOT_FOUND, "Not found.")
        except WebError as exc:
            self._send_error(exc.status, exc.message)
        except Exception as exc:
            self.app.log(f"Request failed: {exc}")
            self._send_error(HTTPStatus.INTERNAL_SERVER_ERROR, str(exc))

    def log_message(self, format: str, *args: Any) -> None:
        self.app.log(format % args)

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0") or "0")
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        try:
            parsed = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise WebError(HTTPStatus.BAD_REQUEST, f"Invalid JSON: {exc}") from exc
        if not isinstance(parsed, dict):
            raise WebError(HTTPStatus.BAD_REQUEST, "JSON body must be an object.")
        return parsed

    def _route_get(self, *, send_body: bool) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        if path in {"/", "/index.html"}:
            self._serve_file(STATIC_ROOT / "index.html", STATIC_ROOT, send_body=send_body)
        elif path.startswith("/static/"):
            requested = STATIC_ROOT / unquote(path.removeprefix("/static/"))
            self._serve_file(requested, STATIC_ROOT, send_body=send_body)
        elif path.startswith("/media/"):
            requested = PROJECT_ROOT / unquote(path.removeprefix("/media/"))
            self._serve_file(requested, PROJECT_ROOT, send_body=send_body)
        elif path == "/api/config":
            self._send_json(self.app.config_payload(), send_body=send_body)
        elif path == "/api/status":
            self._send_json(self.app.status_payload(), send_body=send_body)
        elif path == "/api/defaults":
            self._send_json({"defaults": self.app.load_defaults()}, send_body=send_body)
        elif path == "/api/devices/scan":
            self._send_json(self.app.scan_devices(), send_body=send_body)
        else:
            self._send_error(HTTPStatus.NOT_FOUND, "Not found.")

    def _send_json(
        self,
        payload: dict[str, Any],
        status: HTTPStatus = HTTPStatus.OK,
        *,
        send_body: bool = True,
    ) -> None:
        body = json.dumps(payload, ensure_ascii=False, allow_nan=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if send_body:
            self.wfile.write(body)

    def _send_error(self, status: HTTPStatus, message: str) -> None:
        self._send_json({"ok": False, "error": message}, status=status)

    def _serve_file(self, requested: Path, root: Path, *, send_body: bool = True) -> None:
        try:
            resolved = requested.resolve()
            resolved.relative_to(root.resolve())
        except Exception:
            self._send_error(HTTPStatus.FORBIDDEN, "Forbidden.")
            return
        if not resolved.exists() or not resolved.is_file():
            self._send_error(HTTPStatus.NOT_FOUND, "File not found.")
            return
        content_type = mimetypes.guess_type(str(resolved))[0] or "application/octet-stream"
        body = resolved.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        if content_type.startswith("audio/"):
            self.send_header("Accept-Ranges", "bytes")
        self.end_headers()
        if send_body:
            self.wfile.write(body)


class EEGThreadingHTTPServer(ThreadingHTTPServer):
    app: EEGWebApplication


def create_server(host: str, port: int) -> EEGThreadingHTTPServer:
    app = EEGWebApplication()
    server = EEGThreadingHTTPServer((host, port), EEGRequestHandler)
    server.app = app
    return server


def run(host: str = "127.0.0.1", port: int = 8000, *, open_browser: bool = True) -> None:
    server = create_server(host, port)
    url = f"http://{host}:{server.server_port}"
    print(f"EEG Analyse web app is running at {url}")
    if open_browser:
        threading.Timer(0.4, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping EEG Analyse web app...")
    finally:
        server.server_close()


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Run EEG Analyse as a local web application.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8000, type=int)
    parser.add_argument("--no-browser", action="store_true", help="Do not open a browser automatically.")
    args = parser.parse_args(argv)
    run(args.host, args.port, open_browser=not args.no_browser)


if __name__ == "__main__":
    main()
