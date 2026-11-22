"""Timing configuration UI component."""

from __future__ import annotations

from typing import Callable

import customtkinter as ctk

from app.config_manager import TimingSettings
from app.constants import (
    DEFAULT_INTERVAL_SECONDS,
    MAX_INTERVAL_SECONDS,
    MIN_INTERVAL_SECONDS,
    RECOMMENDED_MIN_INTERVAL_SECONDS,
)
from app.ui.theme import COLORS, font_spec


class TimingPanel(ctk.CTkFrame):
    """Configures message sending interval (default 120s) and initial delay behavior."""

    def __init__(
        self,
        master: ctk.CTkBaseClass,
        initial_timing: TimingSettings,
        on_save_timing: Callable[[int, bool], None],
    ) -> None:
        super().__init__(
            master,
            fg_color=COLORS["bg_card"],
            corner_radius=12,
            border_width=1,
            border_color=COLORS["border"],
        )
        self._on_save = on_save_timing

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=16, pady=(14, 8))

        ctk.CTkLabel(
            header,
            text="Zamanlama",
            font=font_spec(15, "bold"),
            text_color=COLORS["text_primary"],
        ).pack(side="left")

        ctk.CTkLabel(
            header,
            text=f"Varsayılan: {DEFAULT_INTERVAL_SECONDS} sn",
            font=font_spec(11),
            text_color=COLORS["text_muted"],
        ).pack(side="right")

        # Interval input row
        input_row = ctk.CTkFrame(self, fg_color="transparent")
        input_row.pack(fill="x", padx=16, pady=(0, 8))

        ctk.CTkLabel(
            input_row,
            text="Gönderim Aralığı (saniye):",
            font=font_spec(12),
            text_color=COLORS["text_secondary"],
        ).pack(side="left")

        self.interval_var = ctk.StringVar(value=str(initial_timing.interval_seconds))
        self.interval_entry = ctk.CTkEntry(
            input_row,
            textvariable=self.interval_var,
            width=86,
            height=32,
            fg_color=COLORS["bg_input"],
            border_color=COLORS["border"],
            text_color=COLORS["text_primary"],
            font=font_spec(13, "bold", mono=True),
            justify="center",
        )
        self.interval_entry.pack(side="left", padx=(10, 8))

        self.apply_btn = ctk.CTkButton(
            input_row,
            text="Uygula",
            width=80,
            height=32,
            corner_radius=7,
            fg_color=COLORS["info"],
            hover_color=COLORS["info_hover"],
            font=font_spec(12, "bold"),
            command=self._apply,
        )
        self.apply_btn.pack(side="right")

        # Quick presets
        presets_row = ctk.CTkFrame(self, fg_color="transparent")
        presets_row.pack(fill="x", padx=16, pady=(0, 8))

        ctk.CTkLabel(
            presets_row,
            text="Hızlı Seçim:",
            font=font_spec(11),
            text_color=COLORS["text_muted"],
        ).pack(side="left", padx=(0, 6))

        for seconds in (60, 120, 180, 300):
            ctk.CTkButton(
                presets_row,
                text=f"{seconds} sn",
                width=56,
                height=26,
                corner_radius=6,
                fg_color=COLORS["neutral_btn"],
                hover_color=COLORS["neutral_btn_hover"],
                text_color=COLORS["text_primary"],
                font=font_spec(11, "bold"),
                command=lambda s=seconds: self._select_preset(s),
            ).pack(side="left", padx=3)

        # First-message immediate toggle
        self.send_first_var = ctk.BooleanVar(value=initial_timing.send_first_immediately)
        ctk.CTkCheckBox(
            self,
            text="Başlatıldığında ilk mesajı 3 sn içinde gönder",
            variable=self.send_first_var,
            font=font_spec(12),
            text_color=COLORS["text_secondary"],
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            command=self._apply,
        ).pack(anchor="w", padx=16, pady=(2, 4))

        self.feedback_label = ctk.CTkLabel(
            self,
            text="",
            font=font_spec(11),
            text_color=COLORS["text_muted"],
            anchor="w",
            wraplength=360,
            justify="left",
        )
        self.feedback_label.pack(fill="x", padx=16, pady=(2, 12))

        self.interval_entry.bind("<Return>", lambda _e: self._apply())
        self._refresh_warning(initial_timing.interval_seconds)

    def _select_preset(self, seconds: int) -> None:
        self.interval_var.set(str(seconds))
        self._apply()

    def _apply(self) -> None:
        raw = self.interval_var.get().strip()
        try:
            seconds = int(raw)
        except ValueError:
            self.feedback_label.configure(
                text=f"Geçerli bir tam sayı girin ({MIN_INTERVAL_SECONDS}-{MAX_INTERVAL_SECONDS} sn).",
                text_color=COLORS["danger"],
            )
            return

        if seconds < MIN_INTERVAL_SECONDS or seconds > MAX_INTERVAL_SECONDS:
            self.feedback_label.configure(
                text=f"Süre {MIN_INTERVAL_SECONDS} ile {MAX_INTERVAL_SECONDS} saniye arasında olmalıdır.",
                text_color=COLORS["danger"],
            )
            return

        self._on_save(seconds, bool(self.send_first_var.get()))
        self._refresh_warning(seconds)

    def _refresh_warning(self, seconds: int) -> None:
        if seconds < RECOMMENDED_MIN_INTERVAL_SECONDS:
            self.feedback_label.configure(
                text=(
                    f"Uyarı: {seconds} sn kısa bir aralıktır. SonOyuncu reklam kuralları için "
                    f"en az {RECOMMENDED_MIN_INTERVAL_SECONDS}-120 sn önerilir."
                ),
                text_color=COLORS["warning"],
            )
        else:
            self.feedback_label.configure(
                text=f"Aktif gönderim aralığı: her {seconds} saniyede bir mesaj.",
                text_color=COLORS["text_muted"],
            )
