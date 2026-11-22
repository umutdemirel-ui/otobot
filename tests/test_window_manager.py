"""Tests for Minecraft Java Edition window detection and focusing."""

from __future__ import annotations

import unittest
from types import SimpleNamespace

from app.constants import WindowStatus
from app.window_manager import WindowManager


class FakeWindow:
    def __init__(
        self,
        title: str,
        is_minimized: bool = False,
        is_active: bool = False,
        width: int = 1280,
        height: int = 720,
        raise_zero_error: bool = False,
    ) -> None:
        self.title = title
        self.isMinimized = is_minimized
        self.isActive = is_active
        self.width = width
        self.height = height
        self._raise_zero_error = raise_zero_error

    def restore(self) -> None:
        self.isMinimized = False

    def activate(self) -> None:
        if self._raise_zero_error:
            self.isActive = True
            raise RuntimeError("Error code from Windows: 0 - The operation completed successfully.")
        self.isActive = True


class FakeBackend:
    def __init__(self, windows: list[FakeWindow]) -> None:
        self.windows = windows

    def getAllWindows(self) -> list[FakeWindow]:
        return list(self.windows)


class TestWindowManager(unittest.TestCase):
    def test_filters_out_own_app_and_finds_minecraft(self) -> None:
        backend = FakeBackend([
            FakeWindow("SonOyuncu Auto Message Bot v1.0.0", is_active=True),
            FakeWindow("Google Chrome", is_active=False),
            FakeWindow("SonOyuncu Minecraft 1.8.9", is_active=False),
        ])
        wm = WindowManager(backend=backend)
        found = wm.list_minecraft_windows()
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0].title, "SonOyuncu Minecraft 1.8.9")

    def test_handles_pygetwindow_error_code_zero_quirk(self) -> None:
        mc = FakeWindow("Minecraft 1.20.4", is_minimized=True, raise_zero_error=True)
        backend = FakeBackend([mc])
        wm = WindowManager(backend=backend)

        ready, status, _msg, target = wm.ensure_ready(auto_focus=True, focus_delay=0.01)
        self.assertTrue(ready)
        self.assertEqual(status, WindowStatus.READY)
        self.assertIsNotNone(target)
        self.assertFalse(mc.isMinimized)
        self.assertTrue(mc.isActive)

    def test_reports_not_found_when_window_disappears(self) -> None:
        backend = FakeBackend([])
        wm = WindowManager(backend=backend)

        ready, status, _msg, target = wm.ensure_ready()
        self.assertFalse(ready)
        self.assertEqual(status, WindowStatus.NOT_FOUND)
        self.assertIsNone(target)


if __name__ == "__main__":
    unittest.main()
