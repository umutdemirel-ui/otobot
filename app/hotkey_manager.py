"""Global F8 emergency stop hotkey listener."""

from __future__ import annotations

import ctypes
import logging
import sys
import threading
import time
from typing import Any, Callable

logger = logging.getLogger("otobot.hotkey")

VK_F8 = 0x77


class GlobalHotkeyManager:
    """Listens globally for F8 key presses to trigger emergency stop."""

    def __init__(self, on_emergency_stop: Callable[[], None]) -> None:
        self._callback = on_emergency_stop
        self._running = False
        self._stop_event = threading.Event()
        self._listener: Any = None
        self._fallback_thread: threading.Thread | None = None
        self._last_trigger_ts = 0.0
        self._lock = threading.Lock()
        self.backend_name: str = "none"

    def start(self) -> bool:
        """Start listening for global F8 presses."""
        if self._running:
            return True

        self._stop_event.clear()

        if self._try_start_pynput():
            self._running = True
            self.backend_name = "pynput"
            logger.info("Global F8 kısayolu pynput ile başlatıldı.")
            return True

        if sys.platform == "win32" and self._try_start_win32_poll():
            self._running = True
            self.backend_name = "win32_poll"
            logger.info("Global F8 kısayolu Win32 API ile başlatıldı.")
            return True

        logger.warning("Global F8 kısayolu başlatılamadı; yalnızca pencere içi F8 aktif.")
        self.backend_name = "window_only"
        return False

    def stop(self) -> None:
        """Stop all global hotkey listeners safely."""
        self._running = False
        self._stop_event.set()

        if self._listener is not None:
            try:
                self._listener.stop()
            except Exception:
                pass
            self._listener = None

        if self._fallback_thread is not None and self._fallback_thread.is_alive():
            self._fallback_thread.join(timeout=1.0)
            self._fallback_thread = None

    def _trigger(self) -> None:
        now = time.monotonic()
        with self._lock:
            if now - self._last_trigger_ts < 0.35:
                return
            self._last_trigger_ts = now

        logger.warning("F8 acil durdurma tuşu algılandı!")
        try:
            self._callback()
        except Exception:
            logger.exception("F8 acil durdurma callback çalıştırılırken hata")

    def _try_start_pynput(self) -> bool:
        try:
            from pynput import keyboard  # type: ignore

            def on_press(key: Any) -> None:
                if not self._running:
                    return
                if key == keyboard.Key.f8:
                    self._trigger()

            listener = keyboard.Listener(on_press=on_press)
            listener.daemon = True
            listener.start()
            self._listener = listener
            return True
        except Exception as exc:
            logger.debug("pynput başlatılamadı: %s", exc)
            return False

    def _try_start_win32_poll(self) -> bool:
        try:
            user32 = ctypes.windll.user32
        except Exception:
            return False

        def poll_loop() -> None:
            was_pressed = False
            while not self._stop_event.is_set():
                try:
                    state = user32.GetAsyncKeyState(VK_F8)
                    is_pressed = bool(state & 0x8000)
                    if is_pressed and not was_pressed:
                        self._trigger()
                    was_pressed = is_pressed
                except Exception:
                    break
                self._stop_event.wait(0.05)

        thread = threading.Thread(target=poll_loop, name="Win32F8Hotkey", daemon=True)
        thread.start()
        self._fallback_thread = thread
        return True
