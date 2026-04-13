from __future__ import annotations

import asyncio
import contextlib
import io
import logging
import re
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from muselsl import backends
from muselsl.muse import Muse
from muselsl.stream import list_muses


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


class MuseDeviceManager:
    def __init__(
        self,
        python_executable: str | None = None,
        log_sink: Callable[[str], None] | None = None,
        *,
        muselsl_retries: int = 9999,
        restart_delay_seconds: float = 2.0,
    ) -> None:
        self.python_executable = python_executable or sys.executable
        self.log_sink = log_sink or (lambda message: None)
        self.muselsl_retries = muselsl_retries
        self.restart_delay_seconds = restart_delay_seconds
        self.stream_process: subprocess.Popen[str] | None = None
        self.stream_reader_thread: threading.Thread | None = None
        self.restart_thread: threading.Thread | None = None
        self.current_device: MuseDevice | None = None
        self.current_battery_percent: float | None = None
        self.include_ppg = True
        self._stop_requested = False
        self._state_lock = threading.Lock()

    def scan_devices(self) -> list[MuseDevice]:
        try:
            return self._scan_devices_subprocess()
        except Exception as exc:
            self.log_sink(f"CLI scan failed, trying direct fallback: {exc}")
            return self._scan_devices_direct()

    def _scan_devices_direct(self) -> list[MuseDevice]:
        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            with contextlib.redirect_stdout(io.StringIO()):
                devices = list_muses(log_level=logging.ERROR) or []
            return [
                MuseDevice(
                    name=device.get("name", "Unknown Muse"),
                    address=device.get("address", ""),
                    rssi=device.get("rssi"),
                )
                for device in devices
            ]
        finally:
            asyncio.set_event_loop(None)
            loop.close()

    def _scan_devices_subprocess(self) -> list[MuseDevice]:
        command = [self.python_executable, "-m", "muselsl", "list", "--log", "error"]
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            cwd=str(Path.cwd()),
            timeout=25,
            check=False,
        )
        output = f"{result.stdout}\n{result.stderr}"
        return self._parse_cli_scan_output(output)

    def _parse_cli_scan_output(self, output: str) -> list[MuseDevice]:
        devices: list[MuseDevice] = []
        seen_identifiers: set[tuple[str, str]] = set()
        patterns = [
            re.compile(r"Found device\s+(.*?),\s*MAC Address\s+([^\s,]+)", re.IGNORECASE),
            re.compile(r"Found device\s+(.*?),\s*Address\s+([^\s,]+)", re.IGNORECASE),
            re.compile(r"Found device\s+(.*?)\s+\(([^\)]+)\)", re.IGNORECASE),
        ]

        for raw_line in output.splitlines():
            line = raw_line.strip()
            for pattern in patterns:
                match = pattern.search(line)
                if not match:
                    continue
                name = match.group(1).strip()
                address = match.group(2).strip()
                key = (name, address)
                if key in seen_identifiers:
                    break
                seen_identifiers.add(key)
                devices.append(MuseDevice(name=name, address=address))
                break

        return devices

    def connect(self, device: MuseDevice, *, include_ppg: bool = True) -> None:
        self.disconnect()
        self.current_device = device
        self.include_ppg = include_ppg
        self._stop_requested = False
        self._start_stream_process(device, include_ppg, restarted=False)

    def disconnect(self) -> None:
        self._stop_requested = True
        if self.stream_process is None:
            self.current_device = None
            self.current_battery_percent = None
            return

        process = self.stream_process
        self.stream_process = None
        self.current_device = None
        self.current_battery_percent = None
        self.log_sink("Stopping Muse device stream...")
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=2)

    def read_battery_percentage(self, device: MuseDevice, timeout_seconds: float = 4.0) -> float | None:
        if not device.address:
            self.current_battery_percent = None
            self.log_sink("Battery check skipped because the device address is unavailable.")
            return None

        battery_event = threading.Event()
        battery_holder: dict[str, float] = {}

        def handle_control(message: str) -> None:
            match = re.search(r"""['"]bp['"]\s*:\s*([0-9]+(?:\.[0-9]+)?)""", message)
            if not match:
                return
            battery_holder["value"] = float(match.group(1))
            battery_event.set()

        def handle_telemetry(
            _timestamp: float,
            battery: float,
            _fuel_gauge: float,
            _adc_volt: float,
            _temperature: float,
        ) -> None:
            battery_holder["value"] = round(float(battery), 1)
            battery_event.set()

        muse = Muse(
            address=device.address,
            callback_control=handle_control,
            callback_telemetry=handle_telemetry,
            name=device.name,
            backend="auto",
            log_level=logging.ERROR,
        )
        try:
            connected = muse.connect(retries=1)
            if not connected:
                self.log_sink("Battery check skipped because the control connection could not be established.")
                return None
            try:
                muse.start()
            except Exception:
                pass
            muse.ask_control()
            deadline = time.time() + timeout_seconds
            while time.time() < deadline:
                backends.sleep(0.1)
                if battery_event.is_set():
                    break
            battery = battery_holder.get("value")
            self.current_battery_percent = battery
            if battery is not None:
                self.log_sink(f"Battery check: {battery:.0f}%")
            else:
                self.log_sink("Battery check completed, but no battery value was returned by the device.")
            return battery
        except Exception as exc:
            self.log_sink(f"Battery check unavailable: {exc}")
            self.current_battery_percent = None
            return None
        finally:
            try:
                muse.stop()
            except Exception:
                pass
            try:
                muse.disconnect()
            except Exception:
                pass

    def is_connected(self) -> bool:
        return self.stream_process is not None and self.stream_process.poll() is None

    def _start_stream_process(self, device: MuseDevice, include_ppg: bool, *, restarted: bool) -> None:
        command = [self.python_executable, "-m", "muselsl", "stream", "--name", device.name, "--log", "info"]
        if device.address:
            command.extend(["--address", device.address])
        if include_ppg:
            command.append("--ppg")
        command.extend(["--retries", str(self.muselsl_retries)])
        if device.address and "-" in device.address and ":" not in device.address:
            self.log_sink("Using UUID-style Muse identifier detected on macOS.")

        prefix = "Restarting" if restarted else "Starting"
        self.log_sink(f"{prefix} Muse stream for {device.display_name}")
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            text=True,
            bufsize=1,
            cwd=str(Path.cwd()),
        )
        self.stream_process = process
        self.stream_reader_thread = threading.Thread(
            target=self._read_stream_logs,
            args=(process,),
            name="muselsl-stream-log-reader",
            daemon=True,
        )
        self.stream_reader_thread.start()

    def _read_stream_logs(self, process: subprocess.Popen[str]) -> None:
        if process.stdout is None:
            return
        try:
            for raw_line in process.stdout:
                message = raw_line.strip()
                if message:
                    self.log_sink(f"[muselsl] {message}")
        finally:
            return_code = process.poll()
            if return_code not in (0, None):
                self.log_sink(f"Muse stream process exited with code {return_code}")
            with self._state_lock:
                should_restart = (
                    not self._stop_requested
                    and self.current_device is not None
                    and return_code not in (0, None)
                    and (self.stream_process is None or self.stream_process is process or self.stream_process.poll() is not None)
                    and (self.restart_thread is None or not self.restart_thread.is_alive())
                )
                if should_restart:
                    self.restart_thread = threading.Thread(
                        target=self._restart_stream_worker,
                        name="muselsl-stream-restart",
                        daemon=True,
                    )
                    self.restart_thread.start()

    def _restart_stream_worker(self) -> None:
        time_to_wait = self.restart_delay_seconds
        if time_to_wait > 0:
            threading.Event().wait(time_to_wait)
        with self._state_lock:
            if self._stop_requested or self.current_device is None:
                return
            active_process = self.stream_process
            if active_process is not None and active_process.poll() is None:
                return
            device = self.current_device
            include_ppg = self.include_ppg
        self._start_stream_process(device, include_ppg, restarted=True)
