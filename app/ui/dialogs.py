"""Modal dialogs for message editing and compliance notifications."""

from __future__ import annotations

import customtkinter as ctk

from app.constants import (
    MINECRAFT_MAX_CHAT_LENGTH,
    RULES_COMPLIANCE_TEXT,
    SONOYUNCU_SAFE_CHAT_LENGTH,
)
from app.ui.theme import COLORS, font_spec


def _center_over_master(dialog: ctk.CTkToplevel, master: ctk.CTkBaseClass, width: int, height: int) -> None:
    try:
        master.update_idletasks()
        mx = master.winfo_rootx()
        my = master.winfo_rooty()
        mw = master.winfo_width()
        mh = master.winfo_height()
        if mw > 100 and mh > 100:
            x = max(0, mx + (mw - width) // 2)
            y = max(0, my + (mh - height) // 2)
            dialog.geometry(f"{width}x{height}+{x}+{y}")
            return
    except Exception:
        pass
    dialog.geometry(f"{width}x{height}")


class MessageEditorDialog(ctk.CTkToplevel):
    """Modal dialog for creating or editing a chat advertisement message."""

    def __init__(
        self,
        master: ctk.CTkBaseClass,
        title: str = "Mesaj Ekle",
        initial_text: str = "",
        initial_enabled: bool = True,
    ) -> None:
        super().__init__(master)
        self.result: tuple[str, bool] | None = None

        self.title(title)
        _center_over_master(self, master, width=560, height=430)
        self.minsize(480, 390)
        self.resizable(True, True)
        self.configure(fg_color=COLORS["bg_app"])

        self.transient(master)

        container = ctk.CTkFrame(
            self,
            fg_color=COLORS["bg_card"],
            corner_radius=12,
            border_width=1,
            border_color=COLORS["border"],
        )
        container.pack(fill="both", expand=True, padx=16, pady=16)

        # Anchor bottom action buttons FIRST so they are always visible at any DPI/size
        btn_row = ctk.CTkFrame(container, fg_color="transparent")
        btn_row.pack(side="bottom", fill="x", padx=18, pady=(8, 16))

        ctk.CTkLabel(
            btn_row,
            text="Kısayol: Ctrl+Enter",
            font=font_spec(11),
            text_color=COLORS["text_muted"],
        ).pack(side="left")

        ctk.CTkButton(
            btn_row,
            text="İptal",
            width=96,
            height=38,
            fg_color=COLORS["neutral_btn"],
            hover_color=COLORS["neutral_btn_hover"],
            font=font_spec(13, "bold"),
            command=self._on_cancel,
        ).pack(side="right", padx=(8, 0))

        ctk.CTkButton(
            btn_row,
            text="Onayla ve Bitir",
            width=145,
            height=38,
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            text_color="#052E16",
            font=font_spec(13, "bold"),
            command=self._on_save,
        ).pack(side="right")

        # Top header
        ctk.CTkLabel(
            container,
            text=title,
            font=font_spec(16, "bold"),
            text_color=COLORS["text_primary"],
            anchor="w",
        ).pack(fill="x", padx=18, pady=(16, 4))

        ctk.CTkLabel(
            container,
            text="Minecraft sohbetine gönderilecek reklam veya duyuru mesajını girin:",
            font=font_spec(12),
            text_color=COLORS["text_secondary"],
            anchor="w",
        ).pack(fill="x", padx=18, pady=(0, 10))

        # Meta / hint / error packed from bottom-up above buttons so textbox gets remaining space
        self.error_label = ctk.CTkLabel(
            container,
            text="",
            height=18,
            font=font_spec(12),
            text_color=COLORS["danger"],
            anchor="w",
        )
        self.error_label.pack(side="bottom", fill="x", padx=18, pady=(2, 0))

        self.hint_label = ctk.CTkLabel(
            container,
            text="İpucu: SonOyuncu 1.8.9 istemcilerinde güvenli uzunluk ~100 karakterdir.",
            height=20,
            font=font_spec(11),
            text_color=COLORS["text_muted"],
            anchor="w",
        )
        self.hint_label.pack(side="bottom", fill="x", padx=18, pady=(2, 2))

        meta_row = ctk.CTkFrame(container, fg_color="transparent")
        meta_row.pack(side="bottom", fill="x", padx=18, pady=(8, 4))

        self.enabled_var = ctk.BooleanVar(value=initial_enabled)
        ctk.CTkCheckBox(
            meta_row,
            text="Bu mesaj aktif (sıraya dahil)",
            variable=self.enabled_var,
            font=font_spec(12),
            text_color=COLORS["text_primary"],
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
        ).pack(side="left")

        self.char_label = ctk.CTkLabel(
            meta_row,
            text="0 / 256",
            font=font_spec(12, "bold"),
            text_color=COLORS["text_secondary"],
        )
        self.char_label.pack(side="right")

        # Flexible textbox fills the middle space
        self.textbox = ctk.CTkTextbox(
            container,
            height=120,
            corner_radius=8,
            fg_color=COLORS["bg_input"],
            border_width=1,
            border_color=COLORS["border"],
            text_color=COLORS["text_primary"],
            font=font_spec(13),
            wrap="word",
        )
        self.textbox.pack(fill="both", expand=True, padx=18)
        if initial_text:
            self.textbox.insert("1.0", initial_text)

        self.textbox.bind("<KeyRelease>", self._update_char_count)
        self.textbox.bind("<Control-Return>", lambda _e: (self._on_save(), "break")[1])
        self.bind("<Escape>", lambda _e: self._on_cancel())
        self.protocol("WM_DELETE_WINDOW", self._on_cancel)

        self._update_char_count()
        self.after(60, self._focus_modal)

    def _focus_modal(self) -> None:
        try:
            self.grab_set()
            self.focus_force()
            self.textbox.focus_set()
        except Exception:
            pass

    def _update_char_count(self, _event=None) -> None:
        raw = self.textbox.get("1.0", "end-1c").replace("\n", " ").strip()
        length = len(raw)
        self.char_label.configure(text=f"{length} / {MINECRAFT_MAX_CHAT_LENGTH}")

        if length > 0:
            self.error_label.configure(text="")

        if length > MINECRAFT_MAX_CHAT_LENGTH:
            self.char_label.configure(text_color=COLORS["danger"])
            self.hint_label.configure(
                text=f"Uyarı: {MINECRAFT_MAX_CHAT_LENGTH} karakteri aşan kısımlar kesilecektir.",
                text_color=COLORS["danger"],
            )
        elif length > SONOYUNCU_SAFE_CHAT_LENGTH:
            self.char_label.configure(text_color=COLORS["warning"])
            self.hint_label.configure(
                text="Not: 100 karakter üzeri mesajlar eski Minecraft sürümlerinde kırpılabilir.",
                text_color=COLORS["warning"],
            )
        else:
            self.char_label.configure(text_color=COLORS["text_secondary"])
            self.hint_label.configure(
                text="İpucu: SonOyuncu 1.8.9 istemcilerinde güvenli uzunluk ~100 karakterdir.",
                text_color=COLORS["text_muted"],
            )

    def _on_save(self) -> None:
        text = " ".join(self.textbox.get("1.0", "end-1c").splitlines()).strip()
        if not text:
            self.error_label.configure(text="Mesaj metni boş bırakılamaz.")
            return
        if len(text) > MINECRAFT_MAX_CHAT_LENGTH:
            text = text[:MINECRAFT_MAX_CHAT_LENGTH]
        self.result = (text, bool(self.enabled_var.get()))
        self.destroy()

    def _on_cancel(self) -> None:
        self.result = None
        self.destroy()


class DarkAlertDialog(ctk.CTkToplevel):
    """Dark-themed modal notification / rules dialog."""

    def __init__(
        self,
        master: ctk.CTkBaseClass,
        title: str,
        message: str,
        accent_color: str | None = None,
    ) -> None:
        super().__init__(master)
        self.title(title)
        _center_over_master(self, master, width=500, height=320)
        self.minsize(420, 260)
        self.resizable(True, True)
        self.configure(fg_color=COLORS["bg_app"])
        self.transient(master)

        card = ctk.CTkFrame(
            self,
            fg_color=COLORS["bg_card"],
            corner_radius=12,
            border_width=1,
            border_color=COLORS["border"],
        )
        card.pack(fill="both", expand=True, padx=16, pady=16)

        ctk.CTkButton(
            card,
            text="Tamam",
            width=110,
            height=36,
            fg_color=COLORS["info"],
            hover_color=COLORS["info_hover"],
            font=font_spec(13, "bold"),
            command=self.destroy,
        ).pack(side="bottom", anchor="e", padx=18, pady=(8, 16))

        ctk.CTkLabel(
            card,
            text=title,
            font=font_spec(16, "bold"),
            text_color=accent_color or COLORS["text_primary"],
            anchor="w",
        ).pack(fill="x", padx=18, pady=(16, 8))

        ctk.CTkLabel(
            card,
            text=message,
            font=font_spec(13),
            text_color=COLORS["text_secondary"],
            justify="left",
            wraplength=430,
            anchor="nw",
        ).pack(fill="both", expand=True, padx=18, pady=(0, 8))

        self.bind("<Escape>", lambda _e: self.destroy())
        self.bind("<Return>", lambda _e: self.destroy())
        self.after(60, self._focus_modal)

    def _focus_modal(self) -> None:
        try:
            self.grab_set()
            self.focus_force()
        except Exception:
            pass


def show_rules_dialog(master: ctk.CTkBaseClass) -> None:
    """Open the rules and safety compliance dialog."""
    dlg = DarkAlertDialog(
        master=master,
        title="Güvenlik ve Sunucu Kuralları",
        message=RULES_COMPLIANCE_TEXT,
        accent_color=COLORS["accent"],
    )
    master.wait_window(dlg)
