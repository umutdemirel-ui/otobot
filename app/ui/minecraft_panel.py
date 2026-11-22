"""Minecraft Java Edition connection status and safety preferences panel."""

from __future__ import annotations

from typing import Callable

import customtkinter as ctk

from app.config_manager import MinecraftSettings, SafetySettings
from app.constants import SUPPORTED_CHAT_KEYS, WindowStatus
from app.ui.theme import COLORS, font_spec
from app.window_manager import DetectedWindow

AUTO_WINDOW_OPTION = "Otomatik Algıla (Önerilen)"
INPUT_METHOD_LABELS = {
    "clipboard": "Pano (Ctrl+V • Türkçe Uyumlu)",
    "typing": "Doğrudan Yazma (ASCII)",
}
LABEL_TO_INPUT_METHOD = {v: k for k, v in INPUT_METHOD_LABELS.items()}


class MinecraftPanel(ctk.CTkFrame):
    """Displays Minecraft window detection status, input options, and rule consent."""

    def __init__(
        self,
        master: ctk.CTkBaseClass,
        mc_settings: MinecraftSettings,
        safety_settings: SafetySettings,
        on_refresh_windows: Callable[[], None],
        on_settings_changed: Callable[[str, bool, bool, str, str, bool], None],
        on_show_rules: Callable[[], None],
    ) -> None:
        super().__init__(
            master,
            fg_color=COLORS["bg_card"],
            corner_radius=12,
            border_width=1,
            border_color=COLORS["border"],
        )
        self._on_refresh = on_refresh_windows
        self._on_changed = on_settings_changed

        # Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=16, pady=(14, 8))

        ctk.CTkLabel(
            header,
            text="Minecraft Bağlantısı",
            font=font_spec(15, "bold"),
            text_color=COLORS["text_primary"],
        ).pack(side="left")

        ctk.CTkButton(
            header,
            text="↻ Yenile",
            width=76,
            height=28,
            corner_radius=6,
            fg_color=COLORS["neutral_btn"],
            hover_color=COLORS["neutral_btn_hover"],
            font=font_spec(11, "bold"),
            command=self._on_refresh,
        ).pack(side="right")

        # Status card
        status_card = ctk.CTkFrame(
            self,
            fg_color=COLORS["bg_input"],
            corner_radius=8,
            border_width=1,
            border_color=COLORS["border_subtle"],
        )
        status_card.pack(fill="x", padx=16, pady=(0, 10))

        status_top = ctk.CTkFrame(status_card, fg_color="transparent")
        status_top.pack(fill="x", padx=12, pady=(8, 4))

        self.dot_label = ctk.CTkLabel(
            status_top,
            text="●",
            font=font_spec(14, "bold"),
            text_color=COLORS["danger"],
            width=16,
        )
        self.dot_label.pack(side="left")

        self.status_label = ctk.CTkLabel(
            status_top,
            text=WindowStatus.NOT_FOUND.label_tr,
            font=font_spec(12, "bold"),
            text_color=COLORS["text_primary"],
            anchor="w",
        )
        self.status_label.pack(side="left", padx=(6, 0), fill="x", expand=True)

        self.window_title_label = ctk.CTkLabel(
            status_card,
            text="Açık pencere tespit edilmedi.",
            font=font_spec(11),
            text_color=COLORS["text_muted"],
            anchor="w",
            wraplength=340,
            justify="left",
        )
        self.window_title_label.pack(fill="x", padx=12, pady=(0, 8))

        # Window selector dropdown
        sel_row = ctk.CTkFrame(self, fg_color="transparent")
        sel_row.pack(fill="x", padx=16, pady=(0, 8))

        ctk.CTkLabel(
            sel_row,
            text="Hedef Pencere:",
            font=font_spec(12),
            text_color=COLORS["text_secondary"],
            width=105,
            anchor="w",
        ).pack(side="left")

        initial_win = mc_settings.preferred_window_title or AUTO_WINDOW_OPTION
        self.window_var = ctk.StringVar(value=initial_win)
        self.window_menu = ctk.CTkOptionMenu(
            sel_row,
            variable=self.window_var,
            values=[AUTO_WINDOW_OPTION],
            height=30,
            fg_color=COLORS["bg_input"],
            button_color=COLORS["neutral_btn"],
            button_hover_color=COLORS["neutral_btn_hover"],
            text_color=COLORS["text_primary"],
            font=font_spec(12),
            dynamic_resizing=False,
            command=lambda _v: self._emit_change(),
        )
        self.window_menu.pack(side="left", fill="x", expand=True)

        # Chat key & Input method row
        io_row = ctk.CTkFrame(self, fg_color="transparent")
        io_row.pack(fill="x", padx=16, pady=(0, 8))

        ctk.CTkLabel(
            io_row,
            text="Sohbet Tuşu:",
            font=font_spec(12),
            text_color=COLORS["text_secondary"],
        ).pack(side="left")

        self.chat_key_var = ctk.StringVar(value=mc_settings.chat_key)
        self.chat_key_menu = ctk.CTkOptionMenu(
            io_row,
            variable=self.chat_key_var,
            values=SUPPORTED_CHAT_KEYS,
            width=74,
            height=28,
            fg_color=COLORS["bg_input"],
            button_color=COLORS["neutral_btn"],
            button_hover_color=COLORS["neutral_btn_hover"],
            font=font_spec(12, "bold"),
            command=lambda _v: self._emit_change(),
        )
        self.chat_key_menu.pack(side="left", padx=(6, 10))

        self.input_method_var = ctk.StringVar(
            value=INPUT_METHOD_LABELS.get(mc_settings.input_method, INPUT_METHOD_LABELS["clipboard"])
        )
        self.input_method_menu = ctk.CTkOptionMenu(
            io_row,
            variable=self.input_method_var,
            values=list(INPUT_METHOD_LABELS.values()),
            height=28,
            fg_color=COLORS["bg_input"],
            button_color=COLORS["neutral_btn"],
            button_hover_color=COLORS["neutral_btn_hover"],
            font=font_spec(11),
            dynamic_resizing=False,
            command=lambda _v: self._emit_change(),
        )
        self.input_method_menu.pack(side="left", fill="x", expand=True)

        # Checkboxes
        self.auto_focus_var = ctk.BooleanVar(value=mc_settings.auto_focus_before_send)
        ctk.CTkCheckBox(
            self,
            text="Gönderim öncesi Minecraft penceresini öne getir",
            variable=self.auto_focus_var,
            font=font_spec(12),
            text_color=COLORS["text_secondary"],
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            command=self._emit_change,
        ).pack(anchor="w", padx=16, pady=(2, 4))

        self.pause_minimized_var = ctk.BooleanVar(value=mc_settings.pause_if_minimized)
        ctk.CTkCheckBox(
            self,
            text="Pencere simge durumuna küçültülürse duraklat",
            variable=self.pause_minimized_var,
            font=font_spec(12),
            text_color=COLORS["text_secondary"],
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            command=self._emit_change,
        ).pack(anchor="w", padx=16, pady=(2, 8))

        # Rules consent bar
        rules_box = ctk.CTkFrame(
            self,
            fg_color=COLORS["bg_card_alt"],
            corner_radius=8,
            border_width=1,
            border_color=COLORS["border_subtle"],
        )
        rules_box.pack(fill="x", padx=16, pady=(0, 14))

        self.rules_var = ctk.BooleanVar(value=safety_settings.rules_accepted)
        ctk.CTkCheckBox(
            rules_box,
            text="Sunucu kurallarına uygun kullanımı onaylıyorum",
            variable=self.rules_var,
            font=font_spec(12, "bold"),
            text_color=COLORS["text_primary"],
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            command=self._emit_change,
        ).pack(side="left", padx=10, pady=8)

        ctk.CTkButton(
            rules_box,
            text="Kurallar",
            width=66,
            height=24,
            corner_radius=6,
            fg_color=COLORS["neutral_btn"],
            hover_color=COLORS["neutral_btn_hover"],
            font=font_spec(11),
            command=on_show_rules,
        ).pack(side="right", padx=(0, 10), pady=8)

    def _emit_change(self) -> None:
        selected_win = self.window_var.get()
        preferred = "" if selected_win == AUTO_WINDOW_OPTION else selected_win
        input_method = LABEL_TO_INPUT_METHOD.get(self.input_method_var.get(), "clipboard")
        self._on_changed(
            preferred,
            bool(self.auto_focus_var.get()),
            bool(self.pause_minimized_var.get()),
            self.chat_key_var.get(),
            input_method,
            bool(self.rules_var.get()),
        )

    def update_windows(
        self,
        windows: list[DetectedWindow],
        status: WindowStatus,
        active_title: str,
    ) -> None:
        """Update detected Minecraft windows dropdown and live status indicator."""
        options = [AUTO_WINDOW_OPTION] + [w.title for w in windows]
        current = self.window_var.get()
        if current not in options:
            current = AUTO_WINDOW_OPTION
            self.window_var.set(current)
        self.window_menu.configure(values=options)

        self.status_label.configure(text=status.label_tr)
        if status == WindowStatus.READY:
            self.dot_label.configure(text_color=COLORS["accent"])
            self.window_title_label.configure(
                text=f"Aktif pencere: {active_title}",
                text_color=COLORS["text_secondary"],
            )
        elif status in (WindowStatus.UNFOCUSED, WindowStatus.MINIMIZED):
            self.dot_label.configure(text_color=COLORS["warning"])
            self.window_title_label.configure(
                text=f"Tespit edilen pencere: {active_title}",
                text_color=COLORS["text_secondary"],
            )
        elif status == WindowStatus.UNAVAILABLE:
            self.dot_label.configure(text_color=COLORS["text_muted"])
            self.window_title_label.configure(
                text="Windows masaüstü pencere API'si bu ortamda aktif değil.",
                text_color=COLORS["text_muted"],
            )
        else:
            self.dot_label.configure(text_color=COLORS["danger"])
            self.window_title_label.configure(
                text="SonOyuncu / Minecraft Java Edition penceresi bekleniyor...",
                text_color=COLORS["text_muted"],
            )
