"""Keyboard/clipboard chat sender for Minecraft Java Edition."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any, Callable

from app.constants import MINECRAFT_MAX_CHAT_LENGTH

logger = logging.getLogger("otobot.sender")

try:
    import pyautogui  # type: ignore

    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0.04
except Exception:  # pragma: no cover - headless / missing display
    pyautogui = None

try:
    import pyperclip  # type: ignore
except Exception:  # pragma: no cover
    pyperclip = None


class ChatSendAborted(Exception):
    """Raised when sending is aborted mid-sequence (e.g. F8 / Stop)."""


class FailSafeTriggered(Exception):
    """Raised when PyAutoGUI corner fail-safe is triggered."""


@dataclass
class SendResult:
    """Outcome of a single chat dispatch attempt."""

    success: bool
    message: str
    error: str = ""
    aborted: bool = False
    failsafe: bool = False


class ChatSender:
    """Sends text messages into the active Minecraft Java Edition chat box."""

    def __init__(
        self,
        gui_backend: Any | None = None,
        clipboard_backend: Any | None = None,
    ) -> None:
        self._gui = gui_backend if gui_backend is not None else pyautogui
        self._clipboard = clipboard_backend if clipboard_backend is not None else pyperclip

    def is_available(self) -> bool:
        return self._gui is not None

    def send_message(
        self,
        text: str,
        chat_key: str = "t",
        input_method: str = "clipboard",
        chat_open_delay: float = 0.30,
        post_paste_delay: float = 0.10,
        restore_clipboard: bool = True,
        abort_check: Callable[[], bool] | None = None,
    ) -> SendResult:
        """Open Minecraft chat, enter message text, and press Enter."""
        if not self.is_available():
            return SendResult(
                success=False,
                message=text,
                error="PyAutoGUI bu ortamda kullanılamıyor.",
            )

        cleaned = text.strip()
        if not cleaned:
            return SendResult(success=False, message=text, error="Boş mesaj gönderilemez.")

        if len(cleaned) > MINECRAFT_MAX_CHAT_LENGTH:
            cleaned = cleaned[:MINECRAFT_MAX_CHAT_LENGTH]

        previous_clipboard: str | None = None
        should_restore = restore_clipboard and input_method == "clipboard" and self._clipboard is not None

        if should_restore:
            try:
                previous_clipboard = self._clipboard.paste()
            except Exception:
                previous_clipboard = None

        try:
            self._check_abort(abort_check)

            effective_text = cleaned
            key = (chat_key or "t").strip().lower()
            if key == "/" and effective_text.startswith("/"):
                effective_text = effective_text[1:]

            # 1. Open chat box
            self._gui.press(key)
            self._interruptible_sleep(max(0.05, chat_open_delay), abort_check)

            # 2. Enter message
            if input_method == "clipboard" and self._clipboard is not None:
                self._clipboard.copy(effective_text)
                self._interruptible_sleep(0.05, abort_check)
                self._gui.hotkey("ctrl", "v")
                self._interruptible_sleep(max(0.05, post_paste_delay), abort_check)
            else:
                self._gui.write(effective_text, interval=0.015)
                self._interruptible_sleep(max(0.05, post_paste_delay), abort_check)

            self._check_abort(abort_check)

            # 3. Submit chat message
            self._gui.press("enter")
            return SendResult(success=True, message=cleaned)

        except ChatSendAborted:
            # Close chat box gently with Escape if aborted mid-way
            try:
                self._gui.press("esc")
            except Exception:
                pass
            return SendResult(
                success=False,
                message=cleaned,
                error="Mesaj gönderimi iptal edildi.",
                aborted=True,
            )
        except Exception as exc:
            exc_name = type(exc).__name__
            if "FailSafe" in exc_name:
                return SendResult(
                    success=False,
                    message=cleaned,
                    error="PyAutoGUI acil güvenlik (fare köşesi) tetiklendi.",
                    failsafe=True,
                )
            logger.exception("Mesaj gönderilirken hata oluştu")
            return SendResult(success=False, message=cleaned, error=str(exc))
        finally:
            if should_restore and previous_clipboard is not None:
                try:
                    time.sleep(0.05)
                    self._clipboard.copy(previous_clipboard)
                except Exception:
                    pass

    @staticmethod
    def _check_abort(abort_check: Callable[[], bool] | None) -> None:
        if abort_check is not None and abort_check():
            raise ChatSendAborted()

    @classmethod
    def _interruptible_sleep(
        cls,
        duration: float,
        abort_check: Callable[[], bool] | None,
    ) -> None:
        end = time.monotonic() + duration
        while time.monotonic() < end:
            cls._check_abort(abort_check)
            time.sleep(min(0.03, max(0.0, end - time.monotonic())))
