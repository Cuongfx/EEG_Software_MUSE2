from __future__ import annotations

import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from matplotlib.ticker import MaxNLocator
from PyQt6.QtCore import QEasingCurve, QRectF, QSize, Qt, QPropertyAnimation, pyqtProperty
from PyQt6.QtGui import QBrush, QColor, QPainter, QPen, QResizeEvent
from PyQt6.QtWidgets import QAbstractButton, QFrame, QLabel, QSizePolicy, QVBoxLayout


class SignalCanvas(FigureCanvasQTAgg):
    def __init__(self, title: str, color: str, y_limits: tuple[float, float]) -> None:
        self.default_y_limits = y_limits
        self._title_text = title
        self.figure = Figure(figsize=(4.0, 2.0), dpi=100)
        self.axis = self.figure.add_subplot(111)
        super().__init__(self.figure)
        self.setMinimumSize(80, 56)
        self.figure.patch.set_facecolor("#ffffff")
        self.axis.set_facecolor("#fbfdff")
        self.axis.spines["top"].set_visible(False)
        self.axis.spines["right"].set_visible(False)
        self.axis.spines["left"].set_color("#dbe3ec")
        self.axis.spines["bottom"].set_color("#dbe3ec")
        self.axis.tick_params(colors="#728197", labelsize=8)
        self.axis.grid(True, alpha=0.18, color="#94a3b8")
        self.axis.set_title(self._title_text, fontsize=11, color="#0f172a", loc="left", pad=6)
        self.axis.set_xlim(0, 999)
        self.axis.set_ylim(*y_limits)
        self.line, = self.axis.plot([], [], color=color, linewidth=1.8)
        self._last_visual_signature: tuple[int, int] | None = None
        self._refresh_axes_layout()

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self._refresh_axes_layout()

    def _refresh_axes_layout(self) -> None:
        width = max(self.width(), 80)
        height = max(self.height(), 56)
        self._apply_visual_scale(width, height)
        left = 0.17 if width < 280 else 0.14 if width < 420 else 0.105
        bottom = 0.33 if height < 96 else 0.26 if height < 132 else 0.21
        top = 0.74 if height < 96 else 0.81 if height < 132 else 0.87
        self.figure.subplots_adjust(left=left, right=0.975, top=top, bottom=bottom)
        self.figure.set_constrained_layout(False)
        self.draw_idle()

    def _apply_visual_scale(self, width: int, height: int) -> None:
        signature = (width // 40, height // 24)
        if signature == self._last_visual_signature:
            return
        self._last_visual_signature = signature

        shortest = max(1, min(width, height))
        longest = max(width, height)
        title_chars = max(1, len(self._title_text))
        tick_size = max(6, min(11, int(5 + shortest / 38)))
        base_title = 5.0 + shortest / 34.0 + width / 220.0
        length_penalty = min(3.8, max(0.0, (title_chars - 4) * 0.24))
        compact_penalty = 1.0 if width < 360 else 0.0
        title_size = max(8, min(16, int(round(base_title - length_penalty - compact_penalty))))
        title_pad = max(2, min(8, int(1 + height / 42)))
        line_width = max(1.4, min(2.6, shortest / 72.0))
        x_bins = 4 if width < 280 else 5 if width < 430 else 6 if width < 620 else 8
        y_bins = 3 if height < 110 else 4

        self.axis.tick_params(colors="#728197", labelsize=tick_size)
        self.axis.set_title(self._title_text, fontsize=title_size, color="#0f172a", loc="left", pad=title_pad)
        self.axis.title.set_position((0.01, 0.98))
        self.line.set_linewidth(line_width)
        self.axis.xaxis.set_major_locator(MaxNLocator(nbins=x_bins, integer=True, min_n_ticks=3))
        self.axis.yaxis.set_major_locator(MaxNLocator(nbins=y_bins, min_n_ticks=3))

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
        self.axis.set_xlim(0, max(1, max_points - 1))
        if auto_scale and values:
            visible = np.asarray(values, dtype=float)
            lower = float(np.percentile(visible, 5))
            upper = float(np.percentile(visible, 95))
            center = (lower + upper) / 2.0
            robust_span = max(abs(upper - center), abs(center - lower))
            peak_span = float(np.max(np.abs(visible - center))) if visible.size else 0.0
            half_range = max(min_half_range, robust_span * 1.35, peak_span * 1.05)
            self.axis.set_ylim(center - half_range, center + half_range)
        else:
            self.axis.set_ylim(*self.default_y_limits)
        self.draw_idle()


class SlideSwitch(QAbstractButton):
    """iOS-style on/off switch with a sliding circular thumb."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._thumb = 0.0
        self._anim = QPropertyAnimation(self, b"thumbNormalized", self)
        self._anim.setDuration(160)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.toggled.connect(self._animate_to_state)

    def sizeHint(self) -> QSize:
        return QSize(52, 28)

    def minimumSizeHint(self) -> QSize:
        return self.sizeHint()

    def hitButton(self, pos) -> bool:
        return self.rect().contains(pos)

    def getThumbNormalized(self) -> float:
        return self._thumb

    def setThumbNormalized(self, value: float) -> None:
        self._thumb = max(0.0, min(1.0, float(value)))
        self.update()

    thumbNormalized = pyqtProperty(float, getThumbNormalized, setThumbNormalized)

    def _animate_to_state(self, checked: bool) -> None:
        self._anim.stop()
        self._anim.setStartValue(self._thumb)
        self._anim.setEndValue(1.0 if checked else 0.0)
        self._anim.start()

    def paintEvent(self, event) -> None:
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        track_w, track_h = 48.0, 22.0
        x0 = (w - track_w) / 2.0
        y0 = (h - track_h) / 2.0
        track = QRectF(x0, y0, track_w, track_h)
        radius = track_h / 2.0

        if self.isChecked():
            painter.setBrush(QBrush(QColor("#22C55E")))
            painter.setPen(QPen(QColor("#15803D"), 1))
        else:
            painter.setBrush(QBrush(QColor("#E2E8F0")))
            painter.setPen(QPen(QColor("#CBD5E1"), 1))
        painter.drawRoundedRect(track, radius, radius)

        thumb_d = 18.0
        margin = 2.0
        travel = max(0.0, track_w - 2.0 * margin - thumb_d)
        tx = x0 + margin + travel * self._thumb
        ty = y0 + (track_h - thumb_d) / 2.0
        thumb_rect = QRectF(tx, ty, thumb_d, thumb_d)

        painter.setPen(QPen(QColor("#E2E8F0"), 1))
        painter.setBrush(QBrush(QColor("#FFFFFF")))
        painter.drawEllipse(thumb_rect)


class MetricCard(QFrame):
    def __init__(self, title: str, accent: str) -> None:
        super().__init__()
        self.setObjectName("MetricCard")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setMinimumHeight(80)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(4)
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
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumHeight(84)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        self.canvas = SignalCanvas(title=title, color=color, y_limits=y_limits)
        self.canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(self.canvas)
