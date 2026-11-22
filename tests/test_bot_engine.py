"""Tests for BotEngine state machine, ordering, auto-pause, and F8 stop."""

from __future__ import annotations

import queue
import tempfile
import time
import unittest
from pathlib import Path

from app.bot_engine import BotEngine, BotEvent
from app.chat_sender import ChatSender
from app.config_manager import ConfigManager
from app.constants import BotState
from app.window_manager import WindowManager
from tests.test_chat_sender import FakeClipboard, FakeGui
from tests.test_window_manager import FakeBackend, FakeWindow


class TestBotEngine(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.cfg_mgr = ConfigManager(settings_path=Path(self.tmp_dir.name) / "settings.json")
        self.cfg_mgr.config.safety.rules_accepted = True
        self.cfg_mgr.config.timing.interval_seconds = 5
        self.cfg_mgr.config.timing.initial_delay_seconds = 1
        self.cfg_mgr.config.timing.chat_open_delay = 0.01
        self.cfg_mgr.config.timing.pre_send_focus_delay = 0.01
        self.cfg_mgr.config.timing.post_paste_delay = 0.01
        self.cfg_mgr.add_message("Mesaj 1")
        self.cfg_mgr.add_message("Mesaj 2")

        self.mc_window = FakeWindow("SonOyuncu Client", is_active=True)
        self.backend = FakeBackend([self.mc_window])
        self.wm = WindowManager(backend=self.backend)
        self.gui = FakeGui()
        self.clip = FakeClipboard()
        self.sender = ChatSender(gui_backend=self.gui, clipboard_backend=self.clip)
        self.events: queue.Queue[BotEvent] = queue.Queue()
        self.engine = BotEngine(self.cfg_mgr, self.wm, self.sender, self.events)

    def tearDown(self) -> None:
        self.engine.shutdown()
        self.tmp_dir.cleanup()

    def test_requires_rules_consent_before_start(self) -> None:
        self.cfg_mgr.config.safety.rules_accepted = False
        ok, msg = self.engine.start()
        self.assertFalse(ok)
        self.assertIn("kuralları", msg.lower())

    def test_sends_message_and_auto_pauses_when_window_closes(self) -> None:
        ok, _ = self.engine.start()
        self.assertTrue(ok)
        self.assertEqual(self.engine.state, BotState.RUNNING)

        # Wait up to 3s for first message to be sent
        deadline = time.monotonic() + 3.0
        while self.engine.sent_count < 1 and time.monotonic() < deadline:
            time.sleep(0.05)

        self.assertGreaterEqual(self.engine.sent_count, 1)

        # Simulate Minecraft window closing during wait countdown
        self.backend.windows.clear()

        deadline = time.monotonic() + 3.0
        while self.engine.state != BotState.PAUSED and time.monotonic() < deadline:
            time.sleep(0.05)

        self.assertEqual(self.engine.state, BotState.PAUSED)

        # Restore window and resume
        self.backend.windows.append(self.mc_window)
        resumed, _ = self.engine.resume()
        self.assertTrue(resumed)
        self.assertEqual(self.engine.state, BotState.RUNNING)

        # Emergency stop (F8)
        stopped = self.engine.stop("F8 test", emergency=True)
        self.assertTrue(stopped)
        self.assertEqual(self.engine.state, BotState.IDLE)

    def test_sends_enabled_messages_in_exact_order(self) -> None:
        self.cfg_mgr.add_message("Pasif Mesaj", enabled=False)
        self.cfg_mgr.add_message("Mesaj 3", enabled=True)
        self.cfg_mgr.config.timing.interval_seconds = 5
        # Override to speed up multi-send verification
        self.cfg_mgr.config.timing.initial_delay_seconds = 1

        sent_texts: list[str] = []
        original_copy = self.clip.copy

        def track_copy(text: str) -> None:
            if text != "onceki":
                sent_texts.append(text)
            original_copy(text)

        self.clip.copy = track_copy  # type: ignore

        ok, _ = self.engine.start()
        self.assertTrue(ok)

        deadline = time.monotonic() + 7.5
        while self.engine.sent_count < 2 and time.monotonic() < deadline:
            time.sleep(0.05)

        self.engine.stop("Test bitti")
        self.assertGreaterEqual(len(sent_texts), 2)
        self.assertEqual(sent_texts[0], "Mesaj 1")
        self.assertEqual(sent_texts[1], "Mesaj 2")
        self.assertNotIn("Pasif Mesaj", sent_texts)


if __name__ == "__main__":
    unittest.main()
