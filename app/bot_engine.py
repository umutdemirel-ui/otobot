"""Threaded auto-message state machine and worker engine."""

from __future__ import annotations

import logging
import queue
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from app.chat_sender import ChatSender
from app.config_manager import ConfigManager, MessageItem
from app.constants import BotState, WindowStatus
from app.window_manager import WindowManager

logger = logging.getLogger("otobot.engine")


@dataclass
class BotEvent:
    """Thread-safe UI notification event emitted by BotEngine."""

    kind: str  # "state" | "countdown" | "log" | "stats" | "window"
    data: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().strftime("%H:%M:%S"))


class BotEngine:
    """Controls the background auto-message sending lifecycle safely."""

    def __init__(
        self,
        config_manager: ConfigManager,
        window_manager: WindowManager,
        chat_sender: ChatSender,
        event_queue: queue.Queue[BotEvent] | None = None,
    ) -> None:
        self.config_manager = config_manager
        self.window_manager = window_manager
        self.chat_sender = chat_sender
        self.event_queue: queue.Queue[BotEvent] = event_queue or queue.Queue()

        self._lock = threading.RLock()
        self._state: BotState = BotState.IDLE
        self._status_detail: str = "Başlatmaya hazır."
        self._stop_event = threading.Event()
        self._resume_event = threading.Event()
        self._worker_thread: threading.Thread | None = None

        self._sent_count: int = 0
        self._current_index: int = 0
        self._remaining_seconds: int = 0

    @property
    def state(self) -> BotState:
        with self._lock:
            return self._state

    @property
    def sent_count(self) -> int:
        with self._lock:
            return self._sent_count

    @property
    def current_index(self) -> int:
        with self._lock:
            return self._current_index

    @property
    def remaining_seconds(self) -> int:
        with self._lock:
            return self._remaining_seconds

    def start(self) -> tuple[bool, str]:
        """Validate prerequisites and start background worker thread."""
        with self._lock:
            if self._state in (BotState.RUNNING, BotState.PAUSED):
                return False, "Bot zaten aktif durumda."

            cfg = self.config_manager.config
            if not cfg.safety.rules_accepted:
                return False, "Devam etmeden önce kullanım ve sunucu kuralları onayını işaretleyin."

            enabled_msgs = self.config_manager.get_enabled_messages()
            if not enabled_msgs:
                return False, "Gönderilecek en az bir aktif mesaj eklemelisiniz."

            if not self.chat_sender.is_available():
                return False, "Klavye gönderim modülü (PyAutoGUI) kullanılamıyor."

            win_status, target = self.window_manager.inspect_status(
                preferred_title=cfg.minecraft.preferred_window_title
            )
            if win_status in (WindowStatus.NOT_FOUND, WindowStatus.UNAVAILABLE) or target is None:
                return (
                    False,
                    "Açık Minecraft Java Edition / SonOyuncu penceresi bulunamadı.",
                )

            if win_status == WindowStatus.MINIMIZED and cfg.minecraft.pause_if_minimized:
                return (
                    False,
                    "Minecraft penceresi simge durumunda. Lütfen pencereyi açın.",
                )

            self._stop_event.clear()
            self._resume_event.set()
            self._sent_count = 0
            self._current_index = 0
            self._remaining_seconds = 0
            self._set_state_locked(BotState.RUNNING, f"Başlatıldı • Hedef: {target.title}")

            self._worker_thread = threading.Thread(
                target=self._worker_loop,
                name="AutoMessageWorker",
                daemon=True,
            )
            self._worker_thread.start()

        self._emit_log(f"Otomasyon başlatıldı. Hedef pencere: {target.title}", level="info")
        self._emit_stats()
        return True, "Başlatıldı."

    def pause(self, reason: str = "Kullanıcı tarafından duraklatıldı.") -> tuple[bool, str]:
        """Pause sending while preserving queue index and remaining wait time."""
        with self._lock:
            if self._state != BotState.RUNNING:
                return False, "Bot şu anda çalışmıyor."
            self._resume_event.clear()
            self._set_state_locked(BotState.PAUSED, reason)

        self._emit_log(f"Duraklatıldı: {reason}", level="warning")
        return True, reason

    def resume(self) -> tuple[bool, str]:
        """Resume sending if Minecraft window and messages are valid."""
        with self._lock:
            if self._state != BotState.PAUSED:
                return False, "Bot duraklatılmış durumda değil."

            cfg = self.config_manager.config
            enabled_msgs = self.config_manager.get_enabled_messages()
            if not enabled_msgs:
                return False, "Devam etmek için en az bir aktif mesaj gerekli."

            win_status, target = self.window_manager.inspect_status(
                preferred_title=cfg.minecraft.preferred_window_title
            )
            if win_status in (WindowStatus.NOT_FOUND, WindowStatus.UNAVAILABLE) or target is None:
                return False, "Minecraft penceresi bulunamadığı için devam edilemiyor."

            if win_status == WindowStatus.MINIMIZED and cfg.minecraft.pause_if_minimized:
                return False, "Minecraft penceresi hâlâ simge durumunda."

            self._set_state_locked(BotState.RUNNING, f"Devam ediliyor • Hedef: {target.title}")
            self._resume_event.set()

        self._emit_log("Otomasyon devam ettiriliyor.", level="info")
        return True, "Devam ettirildi."

    def stop(self, reason: str = "Kullanıcı tarafından durduruldu.", emergency: bool = False) -> bool:
        """Stop the bot immediately (safe for UI button or global F8 hotkey)."""
        with self._lock:
            if self._state in (BotState.IDLE, BotState.STOPPING):
                return False
            self._stop_event.set()
            self._resume_event.set()
            prefix = "[ACİL DURDURMA - F8] " if emergency else ""
            self._set_state_locked(BotState.STOPPING, f"{prefix}{reason}")

        level = "error" if emergency else "info"
        self._emit_log(f"{'[ACİL DURDURMA - F8] ' if emergency else ''}{reason}", level=level)

        worker = self._worker_thread
        if worker is not None and worker is not threading.current_thread() and worker.is_alive():
            worker.join(timeout=2.0)

        with self._lock:
            if self._state == BotState.STOPPING:
                self._remaining_seconds = 0
                self._set_state_locked(BotState.IDLE, reason)
                self._emit_countdown(0, 0)
        return True

    def shutdown(self) -> None:
        """Cleanly stop worker thread during application exit."""
        self.stop("Uygulama kapatılıyor.", emergency=False)

    # --- Internal worker logic ---

    def _worker_loop(self) -> None:
        logger.info("Bot worker thread started.")
        try:
            cfg = self.config_manager.config
            if cfg.timing.send_first_immediately:
                completed = self._countdown_wait(
                    cfg.timing.initial_delay_seconds,
                    phase_label="İlk mesaj hazırlığı",
                )
                if not completed or self._stop_event.is_set():
                    return
            else:
                completed = self._countdown_wait(
                    cfg.timing.interval_seconds,
                    phase_label="İlk gönderim bekleniyor",
                )
                if not completed or self._stop_event.is_set():
                    return

            while not self._stop_event.is_set():
                if not self._wait_until_running():
                    break

                enabled_msgs = self.config_manager.get_enabled_messages()
                if not enabled_msgs:
                    self.pause("Aktif mesaj kalmadığı için otomatik duraklatıldı.")
                    continue

                message_item = self._pick_next_message(enabled_msgs)
                sent_ok = self._execute_send(message_item, len(enabled_msgs))
                if self._stop_event.is_set():
                    break

                if not sent_ok:
                    # Paused inside _execute_send if recoverable; loop waits on _resume_event
                    continue

                interval = self.config_manager.config.timing.interval_seconds
                completed = self._countdown_wait(interval, phase_label="Sonraki mesaj")
                if not completed and self._stop_event.is_set():
                    break

        except Exception as exc:
            logger.exception("Worker döngüsünde beklenmeyen hata")
            self._emit_log(f"Beklenmeyen hata: {exc}", level="error")
        finally:
            with self._lock:
                self._remaining_seconds = 0
                if self._state != BotState.IDLE:
                    detail = self._status_detail if self._state == BotState.STOPPING else "Durduruldu."
                    self._set_state_locked(BotState.IDLE, detail)
            self._emit_countdown(0, 0)
            logger.info("Bot worker thread exited.")

    def _wait_until_running(self) -> bool:
        while not self._stop_event.is_set():
            if self._resume_event.is_set():
                return True
            self._resume_event.wait(timeout=0.3)
        return False

    def _pick_next_message(self, enabled_msgs: list[MessageItem]) -> MessageItem:
        with self._lock:
            idx = self._current_index % len(enabled_msgs)
            self._current_index = idx
            return enabled_msgs[idx]

    def _execute_send(self, message_item: MessageItem, total_enabled: int) -> bool:
        cfg = self.config_manager.config
        ready, win_status, reason, target = self.window_manager.ensure_ready(
            preferred_title=cfg.minecraft.preferred_window_title,
            auto_focus=cfg.minecraft.auto_focus_before_send,
            pause_if_minimized=cfg.minecraft.pause_if_minimized,
            focus_delay=cfg.timing.pre_send_focus_delay,
        )

        if target is not None:
            self._emit_window(win_status, target.title)
        else:
            self._emit_window(win_status, "")

        if not ready:
            self.pause(reason)
            return False

        if self._stop_event.is_set() or self.state != BotState.RUNNING:
            return False

        self._emit_countdown(0, 0, status_override="Mesaj gönderiliyor...")
        result = self.chat_sender.send_message(
            text=message_item.text,
            chat_key=cfg.minecraft.chat_key,
            input_method=cfg.minecraft.input_method,
            chat_open_delay=cfg.timing.chat_open_delay,
            post_paste_delay=cfg.timing.post_paste_delay,
            restore_clipboard=cfg.safety.restore_clipboard,
            abort_check=lambda: self._stop_event.is_set() or self.state != BotState.RUNNING,
        )

        if result.failsafe:
            self.stop(result.error, emergency=True)
            return False

        if result.aborted:
            return False

        if not result.success:
            self.pause(f"Mesaj gönderilemedi: {result.error}")
            return False

        with self._lock:
            sent_number = (self._current_index % total_enabled) + 1
            self._sent_count += 1
            self._current_index = (self._current_index + 1) % total_enabled

        preview = message_item.text if len(message_item.text) <= 65 else f"{message_item.text[:62]}..."
        self._emit_log(f"Gönderildi (#{sent_number}/{total_enabled}): {preview}", level="success")
        self._emit_stats()
        return True

    def _countdown_wait(self, total_seconds: int, phase_label: str) -> bool:
        """Wait for total_seconds while supporting pause/resume/stop and window monitoring."""
        remaining = max(0, int(total_seconds))
        with self._lock:
            self._remaining_seconds = remaining

        if remaining == 0:
            return True

        last_window_check = time.monotonic()
        last_emitted = -1

        while remaining > 0 and not self._stop_event.is_set():
            if not self._resume_event.is_set():
                if not self._wait_until_running():
                    return False
                # Re-sync after resuming
                last_window_check = time.monotonic()
                last_emitted = -1

            if remaining != last_emitted:
                with self._lock:
                    self._remaining_seconds = remaining
                self._emit_countdown(remaining, total_seconds, status_override=phase_label)
                last_emitted = remaining

            # Sleep in 0.25s slices for instant pause/stop responsiveness
            step_end = time.monotonic() + 1.0
            while time.monotonic() < step_end:
                if self._stop_event.is_set():
                    return False
                if not self._resume_event.is_set():
                    break

                now = time.monotonic()
                if now - last_window_check >= 1.0:
                    last_window_check = now
                    if not self._check_window_alive_during_wait():
                        # Auto-paused; wait until user resumes
                        break

                time.sleep(min(0.2, max(0.0, step_end - now)))

            # Only decrement if we were actually running through the second
            if self._resume_event.is_set() and not self._stop_event.is_set():
                remaining -= 1

        with self._lock:
            self._remaining_seconds = 0
        self._emit_countdown(0, total_seconds)
        return not self._stop_event.is_set()

    def _check_window_alive_during_wait(self) -> bool:
        cfg = self.config_manager.config
        win_status, target = self.window_manager.inspect_status(
            preferred_title=cfg.minecraft.preferred_window_title
        )
        self._emit_window(win_status, target.title if target else "")

        if win_status in (WindowStatus.NOT_FOUND, WindowStatus.UNAVAILABLE):
            self.pause("Minecraft penceresi kapatıldı veya kayboldu — otomatik duraklatıldı.")
            return False

        if win_status == WindowStatus.MINIMIZED and cfg.minecraft.pause_if_minimized:
            self.pause("Minecraft penceresi simge durumuna küçültüldü — otomatik duraklatıldı.")
            return False

        return True

    # --- Event emission helpers ---

    def _set_state_locked(self, new_state: BotState, detail: str) -> None:
        self._state = new_state
        self._status_detail = detail
        self.event_queue.put(
            BotEvent(
                kind="state",
                data={"state": new_state, "detail": detail},
            )
        )

    def _emit_countdown(self, remaining: int, total: int, status_override: str = "") -> None:
        self.event_queue.put(
            BotEvent(
                kind="countdown",
                data={
                    "remaining": remaining,
                    "total": total,
                    "label": status_override,
                },
            )
        )

    def _emit_stats(self) -> None:
        enabled_count = len(self.config_manager.get_enabled_messages())
        with self._lock:
            next_idx = (self._current_index % enabled_count) + 1 if enabled_count else 0
            sent = self._sent_count
        self.event_queue.put(
            BotEvent(
                kind="stats",
                data={
                    "sent_count": sent,
                    "next_index": next_idx,
                    "enabled_count": enabled_count,
                },
            )
        )

    def _emit_window(self, status: WindowStatus, title: str) -> None:
        self.event_queue.put(
            BotEvent(
                kind="window",
                data={"status": status, "title": title},
            )
        )

    def _emit_log(self, message: str, level: str = "info") -> None:
        self.event_queue.put(
            BotEvent(
                kind="log",
                data={"message": message, "level": level},
            )
        )
