"""Main CustomTkinter application window assembling all panels and background services."""

from __future__ import annotations

import logging
import queue
from datetime import datetime

import customtkinter as ctk

from app.bot_engine import BotEngine, BotEvent
from app.chat_sender import ChatSender
from app.config_manager import ConfigManager, MessageItem
from app.constants import APP_SUBTITLE, APP_TITLE, APP_VERSION, BotState
from app.hotkey_manager import GlobalHotkeyManager
from app.ui.control_panel import ControlPanel
from app.ui.dialogs import DarkAlertDialog, MessageEditorDialog, show_rules_dialog
from app.ui.message_panel import MessagePanel
from app.ui.minecraft_panel import MinecraftPanel
from app.ui.theme import COLORS, font_spec
from app.ui.timing_panel import TimingPanel
from app.window_manager import WindowManager

logger = logging.getLogger("otobot.ui")


class MainWindow(ctk.CTk):
    """Root desktop window for SonOyuncu Auto Message Bot."""

    def __init__(self, config_manager: ConfigManager | None = None) -> None:
        super().__init__()

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.config_manager = config_manager or ConfigManager()
        self.event_queue: queue.Queue[BotEvent] = queue.Queue()
        self.window_manager = WindowManager(
            keywords=self.config_manager.config.minecraft.window_keywords
        )
        self.chat_sender = ChatSender()
        self.bot_engine = BotEngine(
            config_manager=self.config_manager,
            window_manager=self.window_manager,
            chat_sender=self.chat_sender,
            event_queue=self.event_queue,
        )
        self.hotkey_manager = GlobalHotkeyManager(on_emergency_stop=self._handle_emergency_stop)
        self._closing = False

        self._configure_window()
        self._build_layout()
        self._bind_events()

        # Initial UI population
        self.message_panel.render_messages(self.config_manager.config.messages)
        self._refresh_windows()
        self._update_stats_from_config()

        # Start services & polling
        self.hotkey_manager.start()
        self._append_log(
            f"Uygulama hazır (v{APP_VERSION}). Acil durdurma tuşu: F8 ({self.hotkey_manager.backend_name}).",
            level="info",
        )
        self.after(80, self._poll_bot_events)
        self.after(2500, self._periodic_window_refresh)

    def _configure_window(self) -> None:
        self.title(f"{APP_TITLE} v{APP_VERSION}")
        self.geometry("1160x760")
        self.minsize(980, 660)
        self.configure(fg_color=COLORS["bg_app"])

    def _build_layout(self) -> None:
        # Top Header Bar
        header = ctk.CTkFrame(
            self,
            fg_color=COLORS["bg_card"],
            corner_radius=0,
            border_width=0,
            height=64,
        )
        header.pack(fill="x", side="top")
        header.pack_propagate(False)

        header_inner = ctk.CTkFrame(header, fg_color="transparent")
        header_inner.pack(fill="both", expand=True, padx=20)

        title_group = ctk.CTkFrame(header_inner, fg_color="transparent")
        title_group.pack(side="left", pady=10)

        ctk.CTkLabel(
            title_group,
            text=APP_TITLE,
            font=font_spec(18, "bold"),
            text_color=COLORS["text_primary"],
            anchor="w",
        ).pack(anchor="w")

        ctk.CTkLabel(
            title_group,
            text=APP_SUBTITLE,
            font=font_spec(11),
            text_color=COLORS["text_secondary"],
            anchor="w",
        ).pack(anchor="w")

        # Right side emergency stop indicator badge
        f8_badge = ctk.CTkLabel(
            header_inner,
            text="🛡  ACİL DURDURMA: F8",
            font=font_spec(12, "bold"),
            fg_color=COLORS["badge_danger_bg"],
            text_color=COLORS["danger"],
            corner_radius=8,
            padx=14,
            pady=6,
        )
        f8_badge.pack(side="right", pady=14)

        # Divider line
        ctk.CTkFrame(self, height=1, fg_color=COLORS["border"]).pack(fill="x")

        # Main 2-column content area
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=16, pady=14)
        body.columnconfigure(0, weight=4, minsize=390)
        body.columnconfigure(1, weight=6, minsize=480)
        body.rowconfigure(0, weight=1)

        # Left column (scrollable safety wrapper for smaller screens)
        left_scroll = ctk.CTkScrollableFrame(
            body,
            fg_color="transparent",
            corner_radius=0,
        )
        left_scroll.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        self.control_panel = ControlPanel(
            left_scroll,
            on_start=self._on_start,
            on_pause=self._on_pause,
            on_resume=self._on_resume,
            on_stop=self._on_stop,
        )
        self.control_panel.pack(fill="x", pady=(0, 12))

        self.timing_panel = TimingPanel(
            left_scroll,
            initial_timing=self.config_manager.config.timing,
            on_save_timing=self._on_save_timing,
        )
        self.timing_panel.pack(fill="x", pady=(0, 12))

        self.minecraft_panel = MinecraftPanel(
            left_scroll,
            mc_settings=self.config_manager.config.minecraft,
            safety_settings=self.config_manager.config.safety,
            on_refresh_windows=self._refresh_windows,
            on_settings_changed=self._on_minecraft_settings_changed,
            on_show_rules=lambda: show_rules_dialog(self),
        )
        self.minecraft_panel.pack(fill="x", pady=(0, 4))

        # Right column: Message Management + Activity Log
        right_col = ctk.CTkFrame(body, fg_color="transparent")
        right_col.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        right_col.rowconfigure(0, weight=3)
        right_col.rowconfigure(1, weight=2)
        right_col.columnconfigure(0, weight=1)

        self.message_panel = MessagePanel(
            right_col,
            on_add=self._on_add_message,
            on_edit=self._on_edit_message,
            on_delete=self._on_delete_message,
            on_toggle=self._on_toggle_message,
            on_move=self._on_move_message,
        )
        self.message_panel.grid(row=0, column=0, sticky="nsew", pady=(0, 12))

        # Activity Log Panel
        log_card = ctk.CTkFrame(
            right_col,
            fg_color=COLORS["bg_card"],
            corner_radius=12,
            border_width=1,
            border_color=COLORS["border"],
        )
        log_card.grid(row=1, column=0, sticky="nsew")

        log_header = ctk.CTkFrame(log_card, fg_color="transparent")
        log_header.pack(fill="x", padx=16, pady=(12, 6))

        ctk.CTkLabel(
            log_header,
            text="İşlem Günlüğü",
            font=font_spec(14, "bold"),
            text_color=COLORS["text_primary"],
        ).pack(side="left")

        ctk.CTkButton(
            log_header,
            text="Temizle",
            width=72,
            height=26,
            corner_radius=6,
            fg_color=COLORS["neutral_btn"],
            hover_color=COLORS["neutral_btn_hover"],
            font=font_spec(11, "bold"),
            command=self._clear_log,
        ).pack(side="right")

        self.log_box = ctk.CTkTextbox(
            log_card,
            fg_color=COLORS["bg_input"],
            border_width=1,
            border_color=COLORS["border_subtle"],
            text_color=COLORS["text_secondary"],
            font=font_spec(12, mono=True),
            corner_radius=8,
            state="disabled",
            wrap="word",
        )
        self.log_box.pack(fill="both", expand=True, padx=16, pady=(0, 14))

    def _bind_events(self) -> None:
        self.bind_all("<F8>", lambda _e: self._handle_emergency_stop())
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # --- Control callbacks ---

    def _on_start(self) -> None:
        ok, msg = self.bot_engine.start()
        if not ok:
            self._append_log(f"Başlatılamadı: {msg}", level="warning")
            dlg = DarkAlertDialog(
                self,
                title="Başlatılamadı",
                message=msg,
                accent_color=COLORS["warning"],
            )
            self.wait_window(dlg)

    def _on_pause(self) -> None:
        self.bot_engine.pause("Kullanıcı tarafından duraklatıldı.")

    def _on_resume(self) -> None:
        ok, msg = self.bot_engine.resume()
        if not ok:
            self._append_log(f"Devam ettirilemedi: {msg}", level="warning")
            dlg = DarkAlertDialog(
                self,
                title="Devam Ettirilemedi",
                message=msg,
                accent_color=COLORS["warning"],
            )
            self.wait_window(dlg)

    def _on_stop(self) -> None:
        self.bot_engine.stop("Kullanıcı tarafından durduruldu.", emergency=False)

    def _handle_emergency_stop(self) -> None:
        if self.bot_engine.state != BotState.IDLE:
            self.bot_engine.stop("F8 acil durdurma tuşuna basıldı.", emergency=True)

    # --- Timing & Minecraft setting callbacks ---

    def _on_save_timing(self, interval_seconds: int, send_first_immediately: bool) -> None:
        cfg = self.config_manager.config
        cfg.timing.interval_seconds = interval_seconds
        cfg.timing.send_first_immediately = send_first_immediately
        self.config_manager.save()
        self._append_log(
            f"Zamanlama güncellendi: {interval_seconds} sn (İlk mesaj hemen: {'Evet' if send_first_immediately else 'Hayır'}).",
            level="info",
        )

    def _on_minecraft_settings_changed(
        self,
        preferred_title: str,
        auto_focus: bool,
        pause_minimized: bool,
        chat_key: str,
        input_method: str,
        rules_accepted: bool,
    ) -> None:
        cfg = self.config_manager.config
        cfg.minecraft.preferred_window_title = preferred_title
        cfg.minecraft.auto_focus_before_send = auto_focus
        cfg.minecraft.pause_if_minimized = pause_minimized
        cfg.minecraft.chat_key = chat_key
        cfg.minecraft.input_method = input_method
        cfg.safety.rules_accepted = rules_accepted
        self.config_manager.save()
        self._refresh_windows()

    # --- Message management callbacks ---

    def _on_add_message(self) -> None:
        dlg = MessageEditorDialog(self, title="Yeni Mesaj Ekle")
        self.wait_window(dlg)
        if dlg.result is None:
            return
        text, enabled = dlg.result
        self.config_manager.add_message(text=text, enabled=enabled)
        self.message_panel.render_messages(self.config_manager.config.messages)
        self._update_stats_from_config()
        self._append_log("Yeni mesaj eklendi.", level="info")

    def _on_edit_message(self, item: MessageItem) -> None:
        dlg = MessageEditorDialog(
            self,
            title="Mesajı Düzenle",
            initial_text=item.text,
            initial_enabled=item.enabled,
        )
        self.wait_window(dlg)
        if dlg.result is None:
            return
        text, enabled = dlg.result
        self.config_manager.update_message(item.id, new_text=text, enabled=enabled)
        self.message_panel.render_messages(self.config_manager.config.messages)
        self._update_stats_from_config()
        self._append_log("Mesaj güncellendi.", level="info")

    def _on_delete_message(self, message_id: str) -> None:
        if self.config_manager.delete_message(message_id):
            self.message_panel.render_messages(self.config_manager.config.messages)
            self._update_stats_from_config()
            self._append_log("Mesaj silindi.", level="info")

    def _on_toggle_message(self, message_id: str, enabled: bool) -> None:
        if self.config_manager.toggle_message(message_id, enabled):
            self.message_panel.render_messages(self.config_manager.config.messages)
            self._update_stats_from_config()

    def _on_move_message(self, message_id: str, direction: int) -> None:
        if self.config_manager.move_message(message_id, direction):
            self.message_panel.render_messages(self.config_manager.config.messages)
            self._update_stats_from_config()

    # --- Window polling & UI queue ---

    def _refresh_windows(self) -> None:
        preferred = self.config_manager.config.minecraft.preferred_window_title
        windows = self.window_manager.list_minecraft_windows()
        status, target = self.window_manager.inspect_status(preferred_title=preferred)
        self.minecraft_panel.update_windows(
            windows=windows,
            status=status,
            active_title=target.title if target else "",
        )

    def _periodic_window_refresh(self) -> None:
        if self._closing:
            return
        try:
            self._refresh_windows()
        except Exception:
            pass
        self.after(2500, self._periodic_window_refresh)

    def _poll_bot_events(self) -> None:
        if self._closing:
            return

        processed = 0
        while processed < 50:
            try:
                event = self.event_queue.get_nowait()
            except queue.Empty:
                break
            self._handle_bot_event(event)
            processed += 1

        self.after(80, self._poll_bot_events)

    def _handle_bot_event(self, event: BotEvent) -> None:
        if event.kind == "state":
            state: BotState = event.data["state"]
            detail: str = event.data["detail"]
            self.control_panel.update_state(state, detail)
        elif event.kind == "countdown":
            self.control_panel.update_countdown(
                remaining=event.data.get("remaining", 0),
                total=event.data.get("total", 0),
                label=event.data.get("label", ""),
            )
        elif event.kind == "stats":
            self.control_panel.update_stats(
                sent_count=event.data.get("sent_count", 0),
                next_index=event.data.get("next_index", 0),
                enabled_count=event.data.get("enabled_count", 0),
            )
        elif event.kind == "window":
            self._refresh_windows()
        elif event.kind == "log":
            self._append_log(
                event.data.get("message", ""),
                level=event.data.get("level", "info"),
                timestamp=event.timestamp,
            )

    def _update_stats_from_config(self) -> None:
        enabled_count = len(self.config_manager.get_enabled_messages())
        next_idx = (self.bot_engine.current_index % enabled_count) + 1 if enabled_count else 0
        self.control_panel.update_stats(
            sent_count=self.bot_engine.sent_count,
            next_index=next_idx,
            enabled_count=enabled_count,
        )

    def _append_log(self, message: str, level: str = "info", timestamp: str | None = None) -> None:
        ts = timestamp or datetime.now().strftime("%H:%M:%S")
        tag_map = {
            "info": "BİLGİ",
            "success": "BAŞARILI",
            "warning": "UYARI",
            "error": "ACİL/HATA",
        }
        tag = tag_map.get(level, "BİLGİ")
        line = f"[{ts}] [{tag}] {message}\n"

        self.log_box.configure(state="normal")
        self.log_box.insert("end", line)
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def _clear_log(self) -> None:
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.configure(state="disabled")

    def _on_close(self) -> None:
        self._closing = True
        try:
            self.hotkey_manager.stop()
        except Exception:
            pass
        try:
            self.bot_engine.shutdown()
        except Exception:
            pass
        try:
            self.config_manager.save()
        except Exception:
            pass
        self.destroy()
