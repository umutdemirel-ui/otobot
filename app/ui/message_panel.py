"""Message Management UI component: add, edit, delete, toggle, and order messages."""

from __future__ import annotations

from typing import Callable

import customtkinter as ctk

from app.config_manager import MessageItem
from app.constants import SONOYUNCU_SAFE_CHAT_LENGTH
from app.ui.theme import COLORS, font_spec


class MessagePanel(ctk.CTkFrame):
    """Manages ordered advertisement/announcement messages for Minecraft chat."""

    def __init__(
        self,
        master: ctk.CTkBaseClass,
        on_add: Callable[[], None],
        on_edit: Callable[[MessageItem], None],
        on_delete: Callable[[str], None],
        on_toggle: Callable[[str, bool], None],
        on_move: Callable[[str, int], None],
    ) -> None:
        super().__init__(
            master,
            fg_color=COLORS["bg_card"],
            corner_radius=12,
            border_width=1,
            border_color=COLORS["border"],
        )
        self._on_add = on_add
        self._on_edit = on_edit
        self._on_delete = on_delete
        self._on_toggle = on_toggle
        self._on_move = on_move

        # Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=16, pady=(14, 6))

        title_col = ctk.CTkFrame(header, fg_color="transparent")
        title_col.pack(side="left", fill="x", expand=True)

        ctk.CTkLabel(
            title_col,
            text="Mesaj Yönetimi",
            font=font_spec(15, "bold"),
            text_color=COLORS["text_primary"],
            anchor="w",
        ).pack(fill="x")

        self.summary_label = ctk.CTkLabel(
            title_col,
            text="0 aktif / 0 toplam mesaj • Sırayla gönderilir",
            font=font_spec(11),
            text_color=COLORS["text_muted"],
            anchor="w",
        )
        self.summary_label.pack(fill="x")

        ctk.CTkButton(
            header,
            text="+ Yeni Mesaj Ekle",
            height=34,
            corner_radius=8,
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            text_color="#052E16",
            font=font_spec(12, "bold"),
            command=self._on_add,
        ).pack(side="right")

        # Scrollable list of messages
        self.list_frame = ctk.CTkScrollableFrame(
            self,
            fg_color=COLORS["bg_input"],
            corner_radius=8,
            border_width=1,
            border_color=COLORS["border_subtle"],
        )
        self.list_frame.pack(fill="both", expand=True, padx=16, pady=(4, 14))

    def render_messages(self, messages: list[MessageItem]) -> None:
        """Rebuild the ordered message list UI cleanly."""
        for child in self.list_frame.winfo_children():
            child.destroy()

        enabled_count = sum(1 for m in messages if m.enabled)
        self.summary_label.configure(
            text=f"{enabled_count} aktif / {len(messages)} toplam mesaj • Belirlenen sırayla gönderilir"
        )

        if not messages:
            empty = ctk.CTkFrame(self.list_frame, fg_color="transparent")
            empty.pack(fill="both", expand=True, pady=48)
            ctk.CTkLabel(
                empty,
                text="Henüz mesaj eklenmedi",
                font=font_spec(14, "bold"),
                text_color=COLORS["text_secondary"],
            ).pack(pady=(0, 4))
            ctk.CTkLabel(
                empty,
                text="Skyblock ada reklamı veya duyuru eklemek için sağ üstteki '+ Yeni Mesaj Ekle' butonuna tıklayın.",
                font=font_spec(12),
                text_color=COLORS["text_muted"],
                wraplength=420,
                justify="center",
            ).pack()
            return

        total = len(messages)
        for index, item in enumerate(messages):
            self._create_message_row(item, index, total)

    def _create_message_row(self, item: MessageItem, index: int, total: int) -> None:
        row_bg = COLORS["bg_card"] if item.enabled else COLORS["bg_card_alt"]
        row = ctk.CTkFrame(
            self.list_frame,
            fg_color=row_bg,
            corner_radius=8,
            border_width=1,
            border_color=COLORS["border"],
        )
        row.pack(fill="x", padx=6, pady=5)

        # Left: order number & enabled checkbox
        left = ctk.CTkFrame(row, fg_color="transparent")
        left.pack(side="left", padx=(10, 8), pady=10)

        order_badge = ctk.CTkLabel(
            left,
            text=f"#{index + 1}",
            width=32,
            height=26,
            corner_radius=6,
            fg_color=COLORS["badge_running_bg"] if item.enabled else COLORS["badge_idle_bg"],
            text_color=COLORS["accent"] if item.enabled else COLORS["text_muted"],
            font=font_spec(12, "bold", mono=True),
        )
        order_badge.pack(side="left", padx=(0, 8))

        toggle_var = ctk.BooleanVar(value=item.enabled)
        ctk.CTkCheckBox(
            left,
            text="",
            width=24,
            variable=toggle_var,
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            command=lambda mid=item.id, v=toggle_var: self._on_toggle(mid, bool(v.get())),
        ).pack(side="left")

        # Center: message text & character length
        center = ctk.CTkFrame(row, fg_color="transparent")
        center.pack(side="left", fill="x", expand=True, pady=8)

        text_color = COLORS["text_primary"] if item.enabled else COLORS["text_muted"]
        ctk.CTkLabel(
            center,
            text=item.text,
            font=font_spec(13),
            text_color=text_color,
            anchor="w",
            justify="left",
            wraplength=330,
        ).pack(fill="x")

        char_len = len(item.text)
        len_color = COLORS["warning"] if char_len > SONOYUNCU_SAFE_CHAT_LENGTH else COLORS["text_muted"]
        status_note = "Aktif" if item.enabled else "Pasif (Atlanır)"
        ctk.CTkLabel(
            center,
            text=f"{char_len} karakter • {status_note}",
            font=font_spec(11),
            text_color=len_color,
            anchor="w",
        ).pack(fill="x", pady=(2, 0))

        # Right: Reorder, Edit, Delete buttons
        actions = ctk.CTkFrame(row, fg_color="transparent")
        actions.pack(side="right", padx=10, pady=10)

        ctk.CTkButton(
            actions,
            text="↑",
            width=28,
            height=28,
            corner_radius=6,
            fg_color=COLORS["neutral_btn"],
            hover_color=COLORS["neutral_btn_hover"],
            font=font_spec(12, "bold"),
            state="normal" if index > 0 else "disabled",
            command=lambda mid=item.id: self._on_move(mid, -1),
        ).pack(side="left", padx=2)

        ctk.CTkButton(
            actions,
            text="↓",
            width=28,
            height=28,
            corner_radius=6,
            fg_color=COLORS["neutral_btn"],
            hover_color=COLORS["neutral_btn_hover"],
            font=font_spec(12, "bold"),
            state="normal" if index < total - 1 else "disabled",
            command=lambda mid=item.id: self._on_move(mid, 1),
        ).pack(side="left", padx=2)

        ctk.CTkButton(
            actions,
            text="Düzenle",
            width=66,
            height=28,
            corner_radius=6,
            fg_color=COLORS["info"],
            hover_color=COLORS["info_hover"],
            font=font_spec(11, "bold"),
            command=lambda m=item: self._on_edit(m),
        ).pack(side="left", padx=(6, 2))

        ctk.CTkButton(
            actions,
            text="Sil",
            width=48,
            height=28,
            corner_radius=6,
            fg_color=COLORS["badge_danger_bg"],
            hover_color=COLORS["danger"],
            text_color=COLORS["danger"],
            font=font_spec(11, "bold"),
            command=lambda mid=item.id: self._on_delete(mid),
        ).pack(side="left", padx=(2, 0))
