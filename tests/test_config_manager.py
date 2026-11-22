"""Tests for JSON configuration persistence and message CRUD."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from app.config_manager import ConfigManager
from app.constants import DEFAULT_INTERVAL_SECONDS, MIN_INTERVAL_SECONDS


class TestConfigManager(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.settings_path = Path(self.tmp_dir.name) / "settings.json"

    def tearDown(self) -> None:
        self.tmp_dir.cleanup()

    def test_creates_default_config_when_missing(self) -> None:
        mgr = ConfigManager(settings_path=self.settings_path)
        self.assertTrue(self.settings_path.exists())
        self.assertEqual(mgr.config.timing.interval_seconds, DEFAULT_INTERVAL_SECONDS)
        self.assertEqual(mgr.config.messages, [])
        self.assertFalse(mgr.config.safety.rules_accepted)

    def test_message_crud_and_ordering(self) -> None:
        mgr = ConfigManager(settings_path=self.settings_path)
        m1 = mgr.add_message("Birinci reklam mesajı")
        m2 = mgr.add_message("İkinci reklam mesajı")
        m3 = mgr.add_message("Üçüncü reklam mesajı", enabled=False)

        self.assertEqual([m.text for m in mgr.get_enabled_messages()], [
            "Birinci reklam mesajı",
            "İkinci reklam mesajı",
        ])

        # Move second message up -> becomes first
        self.assertTrue(mgr.move_message(m2.id, -1))
        self.assertEqual([m.id for m in mgr.config.messages], [m2.id, m1.id, m3.id])

        # Update message
        mgr.update_message(m1.id, "Güncellenmiş mesaj", enabled=True)
        self.assertEqual(mgr.config.messages[1].text, "Güncellenmiş mesaj")

        # Toggle m3 on
        self.assertTrue(mgr.toggle_message(m3.id, True))
        self.assertEqual(len(mgr.get_enabled_messages()), 3)

        # Delete m2
        self.assertTrue(mgr.delete_message(m2.id))
        self.assertEqual([m.id for m in mgr.config.messages], [m1.id, m3.id])

        # Reload from disk and verify persistence
        reloaded = ConfigManager(settings_path=self.settings_path)
        self.assertEqual([m.text for m in reloaded.config.messages], [
            "Güncellenmiş mesaj",
            "Üçüncü reklam mesajı",
        ])

    def test_recovers_from_corrupted_json_with_backup(self) -> None:
        self.settings_path.write_text("{broken json!!!", encoding="utf-8")
        mgr = ConfigManager(settings_path=self.settings_path)
        self.assertEqual(mgr.config.timing.interval_seconds, DEFAULT_INTERVAL_SECONDS)
        self.assertTrue(self.settings_path.with_suffix(".json.bak").exists())

    def test_clamps_invalid_timing_values(self) -> None:
        self.settings_path.write_text(
            json.dumps({"timing": {"interval_seconds": 1}}),
            encoding="utf-8",
        )
        mgr = ConfigManager(settings_path=self.settings_path)
        self.assertEqual(mgr.config.timing.interval_seconds, MIN_INTERVAL_SECONDS)


if __name__ == "__main__":
    unittest.main()
