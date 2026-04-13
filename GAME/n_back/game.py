from __future__ import annotations

import csv
import random
import re
import sys
import time
import tkinter as tk
from datetime import date, datetime
from pathlib import Path
from tkinter import messagebox

from .config import NBackRules, calculate_trial_count, load_rules
from .data import load_participant_tasks, resolve_block_plan
from .master_control import append_master_control_row
from .models import ExaminerSession, SessionStage, TrialResult


class NBackGameController:
    def __init__(self, root: tk.Tk, assets_dir: Path) -> None:
        self.root = root
        self.assets_dir = assets_dir
        self.root.attributes("-fullscreen", True)
        self.root.title("Focus Game")
        self.root.configure(bg="#111827")

        self.rules: NBackRules = load_rules(assets_dir / "rules.txt")
        self.participant_task_data = load_participant_tasks(assets_dir / "participant-task.csv")
        self.total_blocks = 5
        self.master_control_path = assets_dir / "result" / "Master_Control.xlsx"

        self.session: ExaminerSession | None = None
        self.session_ready = False
        self.session_started = False
        self.current_block = 1
        self.n: int | None = None
        self.sequence: list[str] = []
        self.results: list[TrialResult] = []
        self.completed_blocks: list[tuple[int, int, list[TrialResult]]] = []
        self.is_playing = False
        self.current_letter: str | None = None
        self.current_instruction_screen = 0
        self.state = "waiting"
        self.experiment_start_time: str | None = None
        self.date_experiment: str | None = None
        self.current_stage_index = -1
        self.current_stage_duration_minutes = 0.0
        self.current_game_duration_minutes = float(self.rules.actual_minutes)
        self.session_export_path: Path | None = None
        self.game_stage_completed = False
        self.current_game_n_value: int | None = None
        self.game_intro_pages: list[tuple[str, str]] = []
        self.countdown_after_id: str | None = None
        self.stage_transition_after_id: str | None = None
        self.letter_hide_after_id: str | None = None
        self.next_letter_after_id: str | None = None
        self.reset_color_after_id: str | None = None
        self.second_beep_after_id: str | None = None
        self.max_actual_task_trial_number = self._calculate_game_trials(self.current_game_duration_minutes)
        self.max_practice_task_trial_number = calculate_trial_count(
            self.rules.practice_minutes,
            self.rules.display_time_ms,
            self.rules.intertrial_interval_ms,
        )

        self.status_label = tk.Label(
            root,
            text="Waiting for Examiner...",
            font=("Arial", 36, "bold"),
            fg="#F9FAFB",
            bg="#111827",
            justify="center",
            wraplength=1100,
        )
        self.status_label.pack(expand=True, fill="both", padx=40, pady=(80, 16))

        self.detail_label = tk.Label(
            root,
            text="The participant screen will unlock after the examiner confirms the session.",
            font=("Arial", 20),
            fg="#9CA3AF",
            bg="#111827",
            justify="center",
            wraplength=1000,
        )
        self.detail_label.pack(padx=40, pady=(0, 24))

        self.start_button = tk.Button(
            root,
            text="Start Game",
            command=self.begin_session,
            font=("Arial", 24, "bold"),
            bg="#14B8A6",
            fg="#06202A",
            activebackground="#0D9488",
            activeforeground="#ECFEFF",
            relief=tk.FLAT,
            padx=24,
            pady=12,
        )
        self.start_button.pack_forget()

        self.root.bind("<space>", self.on_space_press)
        self.root.bind("<Escape>", lambda event: self.root.attributes("-fullscreen", False))

        self.examiner_window = tk.Toplevel(self.root)
        self.examiner_window.title("Examiner Control")
        self.examiner_window.configure(bg="#F8FAFC")
        self.examiner_window.geometry("680x760")
        self.examiner_window.minsize(640, 720)
        self.examiner_window.protocol("WM_DELETE_WINDOW", self._on_examiner_close)
        self._build_examiner_window()

    def _build_examiner_window(self) -> None:
        container = tk.Frame(self.examiner_window, bg="#F8FAFC")
        container.pack(fill="both", expand=True, padx=26, pady=26)

        title = tk.Label(
            container,
            text="Examiner Control",
            font=("Arial", 26, "bold"),
            fg="#0F172A",
            bg="#F8FAFC",
        )
        title.pack(anchor="w")

        subtitle = tk.Label(
            container,
            text="Fill in participant details and define the Relax, Break, and Game session order before the participant starts.",
            font=("Arial", 12),
            fg="#475569",
            bg="#F8FAFC",
            wraplength=600,
            justify="left",
        )
        subtitle.pack(anchor="w", pady=(8, 18))

        form_card = tk.Frame(container, bg="#FFFFFF", highlightbackground="#D9E2EC", highlightthickness=1)
        form_card.pack(fill="x", pady=(0, 16))

        form = tk.Frame(form_card, bg="#FFFFFF")
        form.pack(fill="x", padx=18, pady=18)

        self.examiner_fields: dict[str, tk.Entry | tk.Text] = {}
        field_specs = [
            ("participant_name", "Name"),
            ("participant_id", "ID"),
            ("age", "Age"),
        ]
        for row_index, (key, label_text) in enumerate(field_specs):
            label = tk.Label(form, text=label_text, font=("Arial", 12, "bold"), fg="#1E293B", bg="#FFFFFF")
            label.grid(row=row_index, column=0, sticky="w", pady=8)
            entry = tk.Entry(form, font=("Arial", 12), width=28, relief=tk.FLAT, bg="#F8FAFC", fg="#0F172A")
            entry.grid(row=row_index, column=1, sticky="ew", pady=8, padx=(16, 0), ipady=8)
            self.examiner_fields[key] = entry

        note_label = tk.Label(form, text="Note", font=("Arial", 12, "bold"), fg="#1E293B", bg="#FFFFFF")
        note_label.grid(row=len(field_specs), column=0, sticky="nw", pady=8)
        note_box = tk.Text(form, font=("Arial", 12), width=28, height=4, relief=tk.FLAT, bg="#F8FAFC", fg="#0F172A")
        note_box.grid(row=len(field_specs), column=1, sticky="ew", pady=8, padx=(16, 0))
        self.examiner_fields["note"] = note_box
        form.grid_columnconfigure(1, weight=1)

        planner_card = tk.Frame(container, bg="#FFFFFF", highlightbackground="#D9E2EC", highlightthickness=1)
        planner_card.pack(fill="x", pady=(0, 16))

        planner = tk.Frame(planner_card, bg="#FFFFFF")
        planner.pack(fill="x", padx=18, pady=18)

        planner_title = tk.Label(
            planner,
            text="Session Planner",
            font=("Arial", 16, "bold"),
            fg="#0F172A",
            bg="#FFFFFF",
        )
        planner.grid_columnconfigure(2, weight=1)
        planner_title.grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 12))

        headers = [("Session", 0), ("Order", 1), ("Duration (minutes)", 2)]
        for text, column in headers:
            tk.Label(planner, text=text, font=("Arial", 11, "bold"), fg="#475569", bg="#FFFFFF").grid(
                row=1, column=column, sticky="w", pady=(0, 8), padx=(0, 12)
            )

        default_stages = [("Relax", 1, 2.0), ("Break", 2, 2.0), ("Game", 3, float(self.rules.actual_minutes))]
        self.stage_fields: dict[str, dict[str, tk.Entry]] = {}
        for row_index, (kind, order, duration) in enumerate(default_stages, start=2):
            tk.Label(planner, text=kind, font=("Arial", 12, "bold"), fg="#111827", bg="#FFFFFF").grid(
                row=row_index, column=0, sticky="w", pady=8
            )
            order_entry = tk.Entry(planner, font=("Arial", 12), width=8, relief=tk.FLAT, bg="#F8FAFC", fg="#0F172A")
            order_entry.insert(0, str(order))
            order_entry.grid(row=row_index, column=1, sticky="w", pady=8, padx=(0, 12), ipady=8)
            duration_entry = tk.Entry(planner, font=("Arial", 12), width=12, relief=tk.FLAT, bg="#F8FAFC", fg="#0F172A")
            duration_entry.insert(0, f"{duration:g}")
            duration_entry.grid(row=row_index, column=2, sticky="ew", pady=8, ipady=8)
            self.stage_fields[kind.lower()] = {"order": order_entry, "duration": duration_entry}

        help_text = tk.Label(
            planner,
            text="Use order 1, 2, and 3 exactly once. Set any stage duration to 0 if you want to skip that stage, but Game must be greater than 0.",
            font=("Arial", 11),
            fg="#64748B",
            bg="#FFFFFF",
            wraplength=580,
            justify="left",
        )
        help_text.grid(row=5, column=0, columnspan=3, sticky="w", pady=(14, 0))

        self.examiner_status_label = tk.Label(
            container,
            text="Awaiting session details.",
            font=("Arial", 12),
            fg="#64748B",
            bg="#F8FAFC",
            justify="left",
            wraplength=620,
        )
        self.examiner_status_label.pack(fill="x", pady=(0, 18))

        footer = tk.Frame(container, bg="#F8FAFC")
        footer.pack(fill="x", side="bottom")

        self.confirm_button = tk.Button(
            footer,
            text="Confirm Session",
            command=self.confirm_examiner_session,
            font=("Arial", 15, "bold"),
            bg="#2563EB",
            fg="#F8FAFC",
            activebackground="#1D4ED8",
            activeforeground="#F8FAFC",
            relief=tk.FLAT,
            padx=16,
            pady=12,
        )
        self.confirm_button.pack(fill="x")

    def _on_examiner_close(self) -> None:
        self.examiner_window.withdraw()

    def confirm_examiner_session(self) -> None:
        if self.session_started:
            messagebox.showinfo(
                "Examiner Control",
                "The game is already running. Open a new game window if you want another session.",
            )
            return

        participant_name = self._entry_value("participant_name")
        participant_id = self._entry_value("participant_id")
        age = self._entry_value("age")
        note = self._entry_value("note")

        if not participant_name:
            messagebox.showerror("Examiner Control", "Name is required.")
            return
        if not participant_id:
            messagebox.showerror("Examiner Control", "ID is required.")
            return
        if not age:
            messagebox.showerror("Examiner Control", "Age is required.")
            return

        stage_plan = self._read_stage_plan()
        if stage_plan is None:
            return

        block_plan = resolve_block_plan(participant_id, self.participant_task_data, self.total_blocks)
        self.session = ExaminerSession(
            participant_name=participant_name,
            participant_id=participant_id,
            age=age,
            note=note,
            block_plan=block_plan,
            session_stages=stage_plan,
        )
        self.session_ready = True
        self.session_started = False
        self.current_stage_index = -1
        self.current_block = 1
        self.completed_blocks.clear()
        self.results.clear()
        self.sequence.clear()
        self.session_export_path = None
        self.game_stage_completed = False
        self.current_game_n_value = block_plan[0] if block_plan else 1

        data_source = "participant-task.csv" if participant_id.isdigit() and int(participant_id) in self.participant_task_data else "generated fallback"
        summary = " -> ".join(f"{stage.kind.title()} ({stage.duration_minutes:g} min)" for stage in stage_plan)
        self.examiner_status_label.config(
            text=(
                f"Session confirmed for {participant_name}.\n"
                f"Order: {summary}\n"
                f"Block plan: {', '.join(str(value) for value in block_plan)} ({data_source})."
            ),
            fg="#0F766E",
        )
        self.status_label.config(text="Examiner confirmed the session.")
        self.detail_label.config(
            text=(
                f"Participant: {participant_name}\n"
                f"Session order: {summary}\n\n"
                "Press Start to begin the full block."
            )
        )
        self.start_button.config(text="Start")
        self.start_button.pack(pady=(0, 48))

    def _read_stage_plan(self) -> list[SessionStage] | None:
        stages: list[SessionStage] = []
        orders: list[int] = []
        for kind in ("relax", "break", "game"):
            order_text = self.stage_fields[kind]["order"].get().strip()
            duration_text = self.stage_fields[kind]["duration"].get().strip()
            try:
                order = int(order_text)
            except ValueError:
                messagebox.showerror("Examiner Control", f"{kind.title()} order must be a whole number.")
                return None
            try:
                duration = float(duration_text)
            except ValueError:
                messagebox.showerror("Examiner Control", f"{kind.title()} duration must be a number.")
                return None
            if order not in (1, 2, 3):
                messagebox.showerror("Examiner Control", f"{kind.title()} order must be 1, 2, or 3.")
                return None
            if duration < 0:
                messagebox.showerror("Examiner Control", f"{kind.title()} duration can not be negative.")
                return None
            orders.append(order)
            stages.append(SessionStage(kind=kind, duration_minutes=duration, order=order))

        if sorted(orders) != [1, 2, 3]:
            messagebox.showerror("Examiner Control", "Relax, Break, and Game must use order 1, 2, and 3 exactly once.")
            return None

        game_stage = next(stage for stage in stages if stage.kind == "game")
        if game_stage.duration_minutes <= 0:
            messagebox.showerror("Examiner Control", "Game duration must be greater than zero.")
            return None

        return sorted((stage for stage in stages if stage.duration_minutes > 0), key=lambda stage: stage.order)

    def begin_session(self) -> None:
        if not self.session_ready or self.session is None:
            return
        self._clear_runtime_callbacks()
        self.session_started = True
        self.current_stage_index = -1
        self.completed_blocks.clear()
        self.results.clear()
        self.sequence.clear()
        self.session_export_path = None
        self.game_stage_completed = False
        self.current_game_n_value = self.session.block_plan[0] if self.session and self.session.block_plan else 1
        self.start_button.pack_forget()
        self.experiment_start_time = datetime.now().strftime("%H:%M:%S")
        self.date_experiment = date.today().strftime("%d/%m/%Y")
        self._emit_command("START_RECORDING")
        self._advance_to_next_stage()

    def _advance_to_next_stage(self) -> None:
        if self.session is None:
            return
        self.stage_transition_after_id = None
        self.current_stage_index += 1
        if self.current_stage_index >= len(self.session.session_stages):
            self.finish_session()
            return

        stage = self.session.session_stages[self.current_stage_index]
        self.current_stage_duration_minutes = stage.duration_minutes
        self.root.configure(bg="#111827")
        if stage.kind == "game":
            self._show_game_intro(stage.duration_minutes)
            return
        self._start_guided_stage(stage.kind, stage.duration_minutes)

    def _start_guided_stage(self, kind: str, duration_minutes: float) -> None:
        self._cancel_after("countdown_after_id")
        self._cancel_after("letter_hide_after_id")
        self._cancel_after("next_letter_after_id")
        self.is_playing = False
        self.state = kind
        total_seconds = max(1, int(round(duration_minutes * 60)))
        if kind == "relax":
            self.status_label.config(text="Please relax untill you hear the sound")
        else:
            self.status_label.config(text="Please Break untill you hear the sound")
        self.detail_label.config(text="")
        self._run_stage_countdown(total_seconds)

    def _run_stage_countdown(self, remaining_seconds: int) -> None:
        if self.state not in {"relax", "break"}:
            return
        minutes, seconds = divmod(remaining_seconds, 60)
        self.detail_label.config(text=f"Time remaining: {minutes:02}:{seconds:02}")
        if remaining_seconds <= 0:
            self._play_stage_end_signal()
            self.detail_label.config(text="Preparing the next session...")
            self.stage_transition_after_id = self.root.after(1000, self._advance_to_next_stage)
            return
        self.countdown_after_id = self.root.after(1000, self._run_stage_countdown, remaining_seconds - 1)

    def _start_game_stage(self, duration_minutes: float) -> None:
        self._cancel_after("countdown_after_id")
        self._cancel_after("stage_transition_after_id")
        self.current_game_duration_minutes = duration_minutes
        self.max_actual_task_trial_number = self._calculate_game_trials(duration_minutes)
        self.current_block = 1
        self.results.clear()
        self.sequence.clear()
        self.n = self.current_game_n_value if self.current_game_n_value is not None else 1
        self.state = "playing"
        self.is_playing = True
        self.sequence = self.generate_sequence(self.max_actual_task_trial_number)
        self.show_next_letter()

    def on_space_press(self, _event) -> None:
        if self.state == "game_intro":
            self._advance_game_intro()
            return
        if self.state == "playing":
            self.check_match()

    def _show_game_intro(self, duration_minutes: float) -> None:
        self._cancel_after("countdown_after_id")
        self._cancel_after("stage_transition_after_id")
        self.state = "game_intro"
        self.is_playing = False
        self.current_game_duration_minutes = duration_minutes
        n_value = self.current_game_n_value if self.current_game_n_value is not None else 1
        self.current_instruction_screen = 0
        self.game_intro_pages = [
            (
                "Game Session",
                (
                    "You are about to begin the Focus Game.\n\n"
                    "Press SPACE to continue through the instructions."
                ),
            ),
            (
                "How To Play",
                (
                    f"This is a {n_value}-back task.\n\n"
                    "A sequence of letters will appear one at a time.\n"
                    f"Press SPACE only when the current letter matches the one shown {n_value} step(s) before."
                ),
            ),
            (
                "Ready To Start",
                (
                    f"Stay focused for {duration_minutes:g} minute(s).\n\n"
                    "Press SPACE when you are ready to start the game."
                ),
            ),
        ]
        self._render_game_intro_page()

    def _render_game_intro_page(self) -> None:
        if not self.game_intro_pages:
            return
        title, detail = self.game_intro_pages[self.current_instruction_screen]
        self.status_label.config(text=title, font=("Arial", 40, "bold"))
        self.detail_label.config(text=detail)
        self.root.configure(bg="#111827")

    def _advance_game_intro(self) -> None:
        if self.state != "game_intro":
            return
        self.current_instruction_screen += 1
        if self.current_instruction_screen >= len(self.game_intro_pages):
            self._start_game_stage(self.current_game_duration_minutes)
            return
        self._render_game_intro_page()

    def generate_sequence(self, num_trials: int) -> list[str]:
        if self.n is None:
            return []

        sequence: list[str] = []
        max_letter_usage = 4
        letters = [chr(index) for index in range(65, 91)]
        letter_counts = {letter: 0 for letter in letters}
        num_matches_desired = int((num_trials - self.n) * (self.rules.match_probability_percent / 100))
        total_matches = 0

        for index in range(num_trials):
            if index < self.n:
                available_letters = [letter for letter in letters if letter_counts[letter] < max_letter_usage]
                letter = random.choice(available_letters)
            else:
                should_match = total_matches < num_matches_desired and random.random() < (
                    num_matches_desired - total_matches
                ) / max(num_trials - index, 1)
                if should_match:
                    letter = sequence[index - self.n]
                    total_matches += 1
                else:
                    available_letters = [
                        letter
                        for letter in letters
                        if letter_counts[letter] < max_letter_usage and letter != sequence[index - self.n]
                    ]
                    letter = random.choice(available_letters) if available_letters else random.choice(letters)
            sequence.append(letter)
            letter_counts[letter] += 1
        return sequence

    def show_next_letter(self) -> None:
        if not self.is_playing or len(self.results) >= len(self.sequence):
            if self.state == "playing":
                self._complete_actual_block()
            return

        self.current_letter = self.sequence[len(self.results)]
        letter_start_time = time.time()
        self.results.append(
            TrialResult(
                letter=self.current_letter,
                match_or_not_match="",
                timestamp_letter_appeared=letter_start_time,
                timestamp_letter_disappeared=None,
                is_key_pressed="No",
            )
        )
        self.status_label.config(text=self.current_letter, font=("Arial", 120, "bold"))
        self.detail_label.config(text="")
        self.letter_hide_after_id = self.root.after(self.rules.display_time_ms, self.hide_letter)

    def hide_letter(self) -> None:
        self.letter_hide_after_id = None
        if self.n is None or not self.results:
            return
        current = self.results[-1]
        current.match_or_not_match = "MATCH" if self.is_match() else "NOT_MATCH"
        current.timestamp_letter_disappeared = time.time()
        self.status_label.config(text="", font=("Arial", 36, "bold"))
        self.next_letter_after_id = self.root.after(self.rules.intertrial_interval_ms, self.show_next_letter)

    def check_match(self) -> None:
        if not self.is_playing or not self.current_letter or not self.results:
            return
        current = self.results[-1]
        if current.is_key_pressed == "Yes":
            return
        is_match = self.is_match()
        self.status_label.config(text=self.current_letter or "", font=("Arial", 120, "bold"))
        self.detail_label.config(text="")
        self.root.configure(bg="#052E16" if is_match else "#7F1D1D")
        current.is_key_pressed = "Yes"
        self.reset_color_after_id = self.root.after(400, lambda: self.root.configure(bg="#111827"))

    def is_match(self) -> bool:
        if self.n is None or len(self.results) <= self.n:
            return False
        previous_letter_index = len(self.results) - self.n - 1
        return self.current_letter == self.sequence[previous_letter_index]

    def _complete_actual_block(self) -> None:
        if self.n is None:
            return
        self._cancel_after("letter_hide_after_id")
        self._cancel_after("next_letter_after_id")
        self.is_playing = False
        block_results = list(self.results)
        self.completed_blocks.append((self.current_block, self.n, block_results))
        self._play_stage_end_signal()
        self.game_stage_completed = True
        self.state = "game_stage_complete"
        self.status_label.config(text="Congratulation, the Block is ended", font=("Arial", 34, "bold"))
        self.detail_label.config(text="Preparing the next session...")
        self.stage_transition_after_id = self.root.after(1000, self._advance_to_next_stage)

    def finish_session(self) -> None:
        self._clear_runtime_callbacks()
        self.state = "game_end"
        self.is_playing = False
        self.session_started = False
        self._emit_command("STOP_RECORDING")
        score = self.calculate_score()
        self.session_export_path = self.export_session_results()
        if self.session is not None:
            append_master_control_row(
                self.master_control_path,
                [
                    self.session.participant_name,
                    self.session.participant_id,
                    self.session.age,
                    f"{score:.2f}",
                    self.session.note,
                ],
            )
        self.status_label.config(text="Congratulation, the Block is ended", font=("Arial", 34, "bold"))
        if self.session_export_path is not None:
            self.detail_label.config(
                text=f"The Experiment is finished. Thank you for your attention!\n\nFinal score: {score:.2f}\n\nSaved: {self.session_export_path.name}"
            )
        else:
            self.detail_label.config(text=f"The Experiment is finished. Thank you for your attention!\n\nFinal score: {score:.2f}")
        self.start_button.pack_forget()
        self.session_ready = False

    def calculate_score(self) -> float:
        trials = [trial for _, _, block_results in self.completed_blocks for trial in block_results]
        if not trials:
            return 0.0
        correct = 0
        for trial in trials:
            if trial.match_or_not_match == "MATCH" and trial.is_key_pressed == "Yes":
                correct += 1
            elif trial.match_or_not_match == "NOT_MATCH" and trial.is_key_pressed == "No":
                correct += 1
        return round((correct / len(trials)) * 100.0, 2)

    def export_session_results(self) -> Path | None:
        if self.session is None or not self.completed_blocks:
            return None

        result_folder = self.assets_dir / "result"
        result_folder.mkdir(exist_ok=True)
        date_token = datetime.now().strftime("%Y-%m-%d")
        arrangement_token = self._session_arrangement_token()
        file_token = self._safe_token(self.session.participant_id)
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
            for block_number, n_value, results in self.completed_blocks:
                for trial_index, result in enumerate(results, start=1):
                    writer.writerow(
                        {
                            "participantName": self.session.participant_name,
                            "participantId": self.session.participant_id,
                            "age": self.session.age,
                            "dateExperimentStart": self.date_experiment or "",
                            "timeExperimentStart": self.experiment_start_time or "",
                            "blockNumber": block_number,
                            "nValue": n_value,
                            "trialNumber": trial_index,
                            "letter": result.letter,
                            "matchOrNotMatch": result.match_or_not_match,
                            "timestampLetterAppeared": result.timestamp_letter_appeared,
                            "timestampLetterDisappeared": result.timestamp_letter_disappeared,
                            "isKeyPressed": result.is_key_pressed,
                            "note": self.session.note,
                            "sessionArrangement": arrangement_token,
                        }
                    )
        return output_file

    def _calculate_game_trials(self, duration_minutes: float) -> int:
        return calculate_trial_count(
            max(duration_minutes, 0.1),
            self.rules.display_time_ms,
            self.rules.intertrial_interval_ms,
        )

    def _session_arrangement_token(self) -> str:
        if self.session is None:
            return "ABC"
        mapping = {"relax": "A", "game": "B", "break": "C"}
        ordered_stages = sorted(self.session.session_stages, key=lambda stage: stage.order)
        return "".join(mapping.get(stage.kind, "X") for stage in ordered_stages)

    def _entry_value(self, key: str) -> str:
        widget = self.examiner_fields[key]
        if isinstance(widget, tk.Text):
            return widget.get("1.0", "end").strip()
        return widget.get().strip()

    @staticmethod
    def _safe_token(value: str) -> str:
        cleaned = re.sub(r"[^A-Za-z0-9_-]+", "_", value.strip())
        return cleaned or "participant"

    @staticmethod
    def _emit_command(command: str) -> None:
        print(f"EEG_CMD:{command}", flush=True)

    def _cancel_after(self, attr_name: str) -> None:
        callback_id = getattr(self, attr_name)
        if callback_id is None:
            return
        try:
            self.root.after_cancel(callback_id)
        except Exception:
            pass
        setattr(self, attr_name, None)

    def _clear_runtime_callbacks(self) -> None:
        for attr_name in (
            "countdown_after_id",
            "stage_transition_after_id",
            "letter_hide_after_id",
            "next_letter_after_id",
            "reset_color_after_id",
            "second_beep_after_id",
        ):
            self._cancel_after(attr_name)

    def _play_stage_end_signal(self) -> None:
        self.root.bell()
        self.examiner_window.bell()
        self._cancel_after("second_beep_after_id")

        def second_beep() -> None:
            self.second_beep_after_id = None
            self.root.bell()
            self.examiner_window.bell()

        self.second_beep_after_id = self.root.after(180, second_beep)


def run_game() -> None:
    assets_dir = Path(__file__).resolve().parent
    try:
        root = tk.Tk()
        NBackGameController(root, assets_dir)
        root.mainloop()
    except Exception as exc:
        try:
            messagebox.showerror("Focus Game", f"Failed to start the game: {exc}")
        except Exception:
            pass
        sys.exit(1)
