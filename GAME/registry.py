from __future__ import annotations

import subprocess
import sys
import os
import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ExaminerPreview:
    heading: str
    subtitle: str
    highlights: tuple[str, ...] = ()


@dataclass(frozen=True)
class GameDefinition:
    game_id: str
    title: str
    description: str
    module_path: Path
    module_name: str
    supported_languages: tuple[str, ...] = ("en", "de", "vi", "zh", "ar", "ko", "ja", "fr", "es", "ru", "it", "pt")
    owner: str | None = None
    source: str | None = None
    examiner_preview: dict[str, ExaminerPreview] | None = None


class GameRegistry:
    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root
        self.games = self._build_games()

    def list_games(self) -> list[GameDefinition]:
        return list(self.games.values())

    def get(self, game_id: str) -> GameDefinition:
        return self.games[game_id]

    def launch(
        self,
        game_id: str,
        language_code: str = "en",
        examiner_setup: dict[str, object] | None = None,
        *,
        demo_mode: bool = False,
        demo_n_value: int | None = None,
    ) -> subprocess.Popen[str]:
        game = self.get(game_id)
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        env["EEG_GAME_LANGUAGE"] = language_code
        if examiner_setup is not None:
            env["EEG_GAME_SESSION_JSON"] = json.dumps(examiner_setup)
        if demo_mode:
            env["EEG_GAME_DEMO_MODE"] = "1"
            if demo_n_value is not None:
                env["EEG_GAME_DEMO_N"] = str(demo_n_value)
        return subprocess.Popen(
            [sys.executable, "-m", game.module_name],
            cwd=str(self.project_root),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            text=True,
            bufsize=1,
            env=env,
        )

    def _build_games(self) -> dict[str, GameDefinition]:
        n_back_path = self.project_root / "GAME" / "n_back" / "main.py"
        return {
            "n_back": GameDefinition(
                game_id="n_back",
                title="Focus Game",
                description="Launch the bundled focus task in a separate game window.",
                module_path=n_back_path,
                module_name="GAME.n_back.main",
                supported_languages=("en", "de", "vi", "zh", "ar", "ko", "ja", "fr", "es", "ru", "it", "pt"),
                owner=None,
                source="Based on danghoanganh36/N-Back-Game: https://github.com/danghoanganh36/N-Back-Game",
                examiner_preview={
                    "en": ExaminerPreview(
                        heading="Examiner Control",
                        subtitle="Fill in participant details and arrange Relax (A), Break (B), and Game (C) before the participant starts.",
                        highlights=(
                            "Participant name, ID, age, and note fields",
                            "Session planner for Relax (A), Break (B), and Game (C)",
                            "Language selection and confirmation before launch",
                        ),
                    ),
                    "de": ExaminerPreview(
                        heading="Leitersteuerung",
                        subtitle="Bitte Teilnehmerdaten eingeben und die Reihenfolge von Entspannung, Pause und Spiel festlegen, bevor der Teilnehmer startet.",
                        highlights=(
                            "Felder fuer Name, ID, Alter und Notiz",
                            "Sitzungsplaner fuer Entspannung, Pause und Spiel",
                            "Sprachauswahl und Bestaetigung vor dem Start",
                        ),
                    ),
                    "vi": ExaminerPreview(
                        heading="Điều khiển Giám sát",
                        subtitle="Nhập thông tin người tham gia và sắp xếp thứ tự Thư giãn, Nghỉ và Game trước khi người chơi bắt đầu.",
                        highlights=(
                            "Trường tên, ID, tuổi và ghi chú",
                            "Bộ lập kế hoạch cho Thư giãn, Nghỉ và Game",
                            "Chọn ngôn ngữ và xác nhận trước khi bắt đầu",
                        ),
                    ),
                    "zh": ExaminerPreview(
                        heading="监考控制",
                        subtitle="请先填写参与者信息，并在参与者开始前设置放松、休息和游戏阶段顺序。",
                        highlights=(
                            "参与者姓名、ID、年龄和备注字段",
                            "放松、休息和游戏的阶段顺序设置",
                            "开始前选择语言并确认会话",
                        ),
                    ),
                    "ar": ExaminerPreview(
                        heading="تحكم المُشرف",
                        subtitle="يرجى إدخال بيانات المشارك وتحديد ترتيب جلسات الاسترخاء والاستراحة واللعبة قبل أن يبدأ المشارك.",
                        highlights=(
                            "حقول الاسم والمعرف والعمر والملاحظة",
                            "مخطط الجلسة لترتيب الاسترخاء والاستراحة واللعبة",
                            "اختيار اللغة وتأكيد الجلسة قبل البدء",
                        ),
                    ),
                },
            ),
        }
