"""Control Panel UI component: Start, Pause, Resume, Stop and live status."""

from __future__ import annotations

from typing import Callable

import customtkinter as ctk

from app.constants import BotState
from app.ui.theme import COLORS, font_spec
from app.utils import format_countdown


class ControlPanel(ctk.CTkFrame):
    """Provides bot lifecycle controls and live status/countdown indicators."""

    def __init__(
        self,
        master: ctk.CTkBaseClass,
        on_start: Callable[[], None],
        on_pause: Callable[[], None],
        on_resume: Callable[[], None],
        on_stop: Callable[[], None],
    ) -> None:
        super().__init__(
            master,
            fg_color=COLORS["bg_card"],
            corner_radius=12,
            border_width=1,
            border_color=COLORS["border"],
        )

        # Header row
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=16, pady=(14, 10))

        ctk.CTkLabel(
            header,
            text="Kontrol Paneli",
            font=font_spec(15, "bold"),
            text_color=COLORS["text_primary"],
        ).pack(side="left")

        self.state_badge = ctk.CTkLabel(
            header,
            text=BotState.IDLE.label_tr,
            font=font_spec(11, "bold"),
            fg_color=COLORS["badge_idle_bg"],
            text_color=COLORS["text_secondary"],
            corner_radius=6,
            padx=10,
            pady=4,
        )
        self.state_badge.pack(side="right")

        # Status & Countdown Box
        status_box = ctk.CTkFrame(
            self,
            fg_color=COLORS["bg_input"],
            corner_radius=8,
            border_width=1,
            border_color=COLORS["border_subtle"],
        )
        status_box.pack(fill="x", padx=16, pady=(0, 12))

        top_metrics = ctk.CTkFrame(status_box, fg_color="transparent")
        top_metrics.pack(fill="x", padx=12, pady=(10, 4))

        left_col = ctk.CTkFrame(top_metrics, fg_color="transparent")
        left_col.pack(side="left", fill="x", expand=True)

        self.phase_label = ctk.CTkLabel(
            left_col,
            text="Durum",
            font=font_spec(11),
            text_color=COLORS["text_muted"],
            anchor="w",
        )
        self.phase_label.pack(fill="x")

        self.detail_label = ctk.CTkLabel(
            left_col,
            text="Başlatmaya hazır.",
            font=font_spec(12, "bold"),
            text_color=COLORS["text_primary"],
            anchor="w",
            wraplength=260,
            justify="left",
        )
        self.detail_label.pack(fill="x")

        right_col = ctk.CTkFrame(top_metrics, fg_color="transparent")
        right_col.pack(side="right", padx=(10, 0))

        ctk.CTkLabel(
            right_col,
            text="Kalan Süre",
            font=font_spec(11),
            text_color=COLORS["text_muted"],
            anchor="e",
        ).pack(fill="x")

        self.countdown_label = ctk.CTkLabel(
            right_col,
            text="00:00",
            font=font_spec(20, "bold", mono=True),
            text_color=COLORS["accent"],
            anchor="e",
        )
        self.countdown_label.pack(fill="x")

        self.progress_bar = ctk.CTkProgressBar(
            status_box,
            height=6,
            corner_radius=3,
            fg_color=COLORS["border_subtle"],
            progress_color=COLORS["accent"],
        )
        self.progress_bar.pack(fill="x", padx=12, pady=(6, 8))
        self.progress_bar.set(0.0)

        stats_row = ctk.CTkFrame(status_box, fg_color="transparent")
        stats_row.pack(fill="x", padx=12, pady=(0, 10))

        self.sent_label = ctk.CTkLabel(
            stats_row,
            text="Gönderilen: 0",
            font=font_spec(12),
            text_color=COLORS["text_secondary"],
        )
        self.sent_label.pack(side="left")

        self.next_label = ctk.CTkLabel(
            stats_row,
            text="Sıradaki: -",
            font=font_spec(12),
            text_color=COLORS["text_secondary"],
        )
        self.next_label.pack(side="right")

        # Action Buttons (2x2 clean grid)
        btn_grid = ctk.CTkFrame(self, fg_color="transparent")
        btn_grid.pack(fill="x", padx=16, pady=(0, 14))
        btn_grid.columnconfigure(0, weight=1)
        btn_grid.columnconfigure(1, weight=1)

        self.btn_start = ctk.CTkButton(
            btn_grid,
            text="▶  Başlat",
            height=38,
            corner_radius=8,
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            text_color="#052E16",
            font=font_spec(13, "bold"),
            command=on_start,
        )
        self.btn_start.grid(row=0, column=0, padx=(0, 6), pady=(0, 8), sticky="ew")

        self.btn_pause = ctk.CTkButton(
            btn_grid,
            text="⏸  Duraklat",
            height=38,
            corner_radius=8,
            fg_color=COLORS["warning"],
            hover_color=COLORS["warning_hover"],
            text_color="#1F1600",
            font=font_spec(13, "bold"),
            command=on_pause,
            state="disabled",
        )
        self.btn_pause.grid(row=0, column=1, padx=(6, 0), pady=(0, 8), sticky="ew")

        self.btn_resume = ctk.CTkButton(
            btn_grid,
            text="⏯  Devam Et",
            height=38,
            corner_radius=8,
            fg_color=COLORS["info"],
            hover_color=COLORS["info_hover"],
            text_color=COLORS["text_primary"],
            font=font_spec(13, "bold"),
            command=on_resume,
            state="disabled",
        )
        self.btn_resume.grid(row=1, column=0, padx=(0, 6), sticky="ew")

        self.btn_stop = ctk.CTkButton(
            btn_grid,
            text="⏹  Durdur (F8)",
            height=38,
            corner_radius=8,
            fg_color=COLORS["danger"],
            hover_color=COLORS["danger_hover"],
            text_color=COLORS["text_primary"],
            font=font_spec(13, "bold"),
            command=on_stop,
            state="disabled",
        )
        self.btn_stop.grid(row=1, column=1, padx=(6, 0), sticky="ew")

    def update_state(self, state: BotState, detail: str) -> None:
        """Refresh badge, detail text, and button availability for the current BotState."""
        self.detail_label.configure(text=detail)
        self.state_badge.configure(text=state.label_tr)

        if state == BotState.IDLE:
            self.state_badge.configure(
                fg_color=COLORS["badge_idle_bg"],
                text_color=COLORS["text_secondary"],
            )
            self.btn_start.configure(state="normal")
            self.btn_pause.configure(state="disabled")
            self.btn_resume.configure(state="disabled")
            self.btn_stop.configure(state="disabled")
            self.progress_bar.set(0.0)
            self.countdown_label.configure(text="00:00", text_color=COLORS["text_secondary"])
            self.phase_label.configure(text="Durum")
        elif state == BotState.RUNNING:
            self.state_badge.configure(
                fg_color=COLORS["badge_running_bg"],
                text_color=COLORS["accent"],
            )
            self.btn_start.configure(state="disabled")
            self.btn_pause.configure(state="normal")
            self.btn_resume.configure(state="disabled")
            self.btn_stop.configure(state="normal")
            self.countdown_label.configure(text_color=COLORS["accent"])
        elif state == BotState.PAUSED:
            self.state_badge.configure(
                fg_color=COLORS["badge_paused_bg"],
                text_color=COLORS["warning"],
            )
            self.btn_start.configure(state="disabled")
            self.btn_pause.configure(state="disabled")
            self.btn_resume.configure(state="normal")
            self.btn_stop.configure(state="normal")
            self.countdown_label.configure(text_color=COLORS["warning"])
            self.phase_label.configure(text="Duraklatıldı")
        elif state == BotState.STOPPING:
            self.state_badge.configure(
                fg_color=COLORS["badge_danger_bg"],
                text_color=COLORS["danger"],
            )
            self.btn_start.configure(state="disabled")
            self.btn_pause.configure(state="disabled")
            self.btn_resume.configure(state="disabled")
            self.btn_stop.configure(state="disabled")

    def update_countdown(self, remaining: int, total: int, label: str = "") -> None:
        """Update remaining time display and progress bar."""
        self.countdown_label.configure(text=format_countdown(remaining))
        if label:
            self.phase_label.configure(text=label)
        if total > 0:
            ratio = max(0.0, min(1.0, (total - remaining) / total))
            self.progress_bar.set(ratio)
        else:
            self.progress_bar.set(0.0)

    def update_stats(self, sent_count: int, next_index: int, enabled_count: int) -> None:
        """Update sent message counter and next message order indicator."""
        self.sent_label.configure(text=f"Gönderilen: {sent_count}")
        if enabled_count > 0 and next_index > 0:
            self.next_label.configure(text=f"Sıradaki: #{next_index} / {enabled_count}")
        else:
            self.next_label.configure(text="Sıradaki: -")
