"""Tests for ChatSender keyboard/clipboard behavior."""

from __future__ import annotations

import unittest

from app.chat_sender import ChatSender


class FakeGui:
    def __init__(self) -> None:
        self.events: list[tuple] = []

    def press(self, key: str) -> None:
        self.events.append(("press", key))

    def hotkey(self, *keys: str) -> None:
        self.events.append(("hotkey", keys))

    def write(self, text: str, interval: float = 0.0) -> None:
        self.events.append(("write", text))


class FakeClipboard:
    def __init__(self, initial: str = "onceki") -> None:
        self.value = initial

    def paste(self) -> str:
        return self.value

    def copy(self, text: str) -> None:
        self.value = text


class TestChatSender(unittest.TestCase):
    def test_clipboard_send_supports_turkish_and_restores_clipboard(self) -> None:
        gui = FakeGui()
        clip = FakeClipboard(initial="eski_pano")
        sender = ChatSender(gui_backend=gui, clipboard_backend=clip)

        result = sender.send_message(
            "/ad Şahane Skyblock adası açıldı! ığüşöç",
            chat_key="t",
            input_method="clipboard",
            chat_open_delay=0.01,
            post_paste_delay=0.01,
            restore_clipboard=True,
        )

        self.assertTrue(result.success)
        self.assertEqual(gui.events[0], ("press", "t"))
        self.assertEqual(gui.events[1], ("hotkey", ("ctrl", "v")))
        self.assertEqual(gui.events[2], ("press", "enter"))
        self.assertEqual(clip.value, "eski_pano")

    def test_slash_chat_key_avoids_double_slash(self) -> None:
        gui = FakeGui()
        clip = FakeClipboard()
        sender = ChatSender(gui_backend=gui, clipboard_backend=clip)

        result = sender.send_message(
            "/ad Ada reklamı",
            chat_key="/",
            input_method="typing",
            chat_open_delay=0.01,
            post_paste_delay=0.01,
        )
        self.assertTrue(result.success)
        self.assertEqual(gui.events[0], ("press", "/"))
        self.assertEqual(gui.events[1], ("write", "ad Ada reklamı"))
        self.assertEqual(gui.events[2], ("press", "enter"))

    def test_abort_mid_send_presses_escape_and_does_not_submit(self) -> None:
        gui = FakeGui()
        clip = FakeClipboard()
        sender = ChatSender(gui_backend=gui, clipboard_backend=clip)

        calls = {"count": 0}

        def abort_after_open() -> bool:
            calls["count"] += 1
            return calls["count"] >= 2

        result = sender.send_message(
            "Test mesajı",
            chat_open_delay=0.05,
            abort_check=abort_after_open,
        )
        self.assertFalse(result.success)
        self.assertTrue(result.aborted)
        self.assertIn(("press", "esc"), gui.events)
        self.assertNotIn(("press", "enter"), gui.events)


if __name__ == "__main__":
    unittest.main()
