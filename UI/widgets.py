from __future__ import annotations

import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PyQt6.QtWidgets import QFrame, QLabel, QSizePolicy, QVBoxLayout


class SignalCanvas(FigureCanvasQTAgg):
    def __init__(self, title: str, color: str, y_limits: tuple[float, float]) -> None:
        self.default_y_limits = y_limits
        self.figure = Figure(figsize=(5, 2.1), dpi=100)
        self.axis = self.figure.add_subplot(111)
        super().__init__(self.figure)
        self.figure.patch.set_facecolor("#ffffff")
        self.axis.set_facecolor("#fbfdff")
        self.axis.spines["top"].set_visible(False)
        self.axis.spines["right"].set_visible(False)
        self.axis.spines["left"].set_color("#dbe3ec")
        self.axis.spines["bottom"].set_color("#dbe3ec")
        self.axis.tick_params(colors="#728197", labelsize=8)
        self.axis.grid(True, alpha=0.18, color="#94a3b8")
        self.axis.set_title(title, fontsize=11, color="#0f172a", loc="left", pad=10)
        self.axis.set_xlim(0, 1000)
        self.axis.set_ylim(*y_limits)
        self.line, = self.axis.plot([], [], color=color, linewidth=1.8)
        self.figure.tight_layout()

    def update_series(
        self,
        values: list[float],
        max_points: int,
        *,
        auto_scale: bool = False,
        min_half_range: float = 20.0,
    ) -> None:
        if values:
            padded = np.pad(np.asarray(values, dtype=float), (max_points - len(values), 0), "constant")
        else:
            padded = np.zeros(max_points)
        self.line.set_data(range(max_points), padded)
        self.axis.set_xlim(0, max_points)
        if auto_scale and values:
            visible = np.asarray(values, dtype=float)
            center = float(np.median(visible))
            max_offset = float(np.max(np.abs(visible - center))) if visible.size else 0.0
            half_range = max(min_half_range, max_offset * 1.35)
            self.axis.set_ylim(center - half_range, center + half_range)
        else:
            self.axis.set_ylim(*self.default_y_limits)
        self.draw_idle()


class MetricCard(QFrame):
    def __init__(self, title: str, accent: str) -> None:
        super().__init__()
        self.setObjectName("MetricCard")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(6)
        self.title_label = QLabel(title)
        self.title_label.setObjectName("MetricTitle")
        self.value_label = QLabel("--")
        self.value_label.setObjectName("MetricValue")
        self.caption_label = QLabel("")
        self.caption_label.setObjectName("MetricCaption")
        self.value_label.setStyleSheet(f"color: {accent};")
        layout.addWidget(self.title_label)
        layout.addWidget(self.value_label)
        layout.addWidget(self.caption_label)

    def set_value(self, value: str, caption: str = "") -> None:
        self.value_label.setText(value)
        self.caption_label.setText(caption)


class PlotCard(QFrame):
    def __init__(self, title: str, color: str, y_limits: tuple[float, float]) -> None:
        super().__init__()
        self.setObjectName("PlotCard")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        self.canvas = SignalCanvas(title=title, color=color, y_limits=y_limits)
        self.canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(self.canvas)
