"""Minecraft Java Edition / SonOyuncu window detection and focus management."""

from __future__ import annotations

import ctypes
import logging
import sys
import time
from dataclasses import dataclass
from typing import Any, Protocol

from app.constants import DEFAULT_WINDOW_KEYWORDS, EXCLUDED_WINDOW_KEYWORDS, WindowStatus

logger = logging.getLogger("otobot.window")

try:
    import pygetwindow as gw  # type: ignore
except Exception:  # pragma: no cover - platform dependent import
    gw = None


class WindowLike(Protocol):
    """Minimal protocol representing a PyGetWindow window object."""

    title: str
    isMinimized: bool
    isActive: bool

    def activate(self) -> None: ...
    def restore(self) -> None: ...


@dataclass
class DetectedWindow:
    """Snapshot of a detected Minecraft window."""

    title: str
    is_minimized: bool
    is_active: bool
    handle: Any = None
    native_window: Any = None

    @property
    def status(self) -> WindowStatus:
        if self.is_minimized:
            return WindowStatus.MINIMIZED
        if self.is_active:
            return WindowStatus.READY
        return WindowStatus.UNFOCUSED


class WindowManager:
    """Discovers and safely activates Minecraft Java Edition windows."""

    def __init__(
        self,
        keywords: list[str] | None = None,
        excluded_keywords: list[str] | None = None,
        backend: Any | None = None,
    ) -> None:
        self.keywords = keywords or list(DEFAULT_WINDOW_KEYWORDS)
        self.excluded_keywords = excluded_keywords or list(EXCLUDED_WINDOW_KEYWORDS)
        self._gw = backend if backend is not None else gw

    def is_available(self) -> bool:
        return self._gw is not None and hasattr(self._gw, "getAllWindows")

    def list_minecraft_windows(self) -> list[DetectedWindow]:
        """Return all open windows matching Minecraft Java Edition / SonOyuncu."""
        if not self.is_available():
            return []

        try:
            all_windows = self._gw.getAllWindows()
        except NotImplementedError:
            return []
        except Exception as exc:
            logger.warning("Pencereler listelenirken hata: %s", exc)
            return []

        matched: list[DetectedWindow] = []
        for win in all_windows:
            title = (getattr(win, "title", "") or "").strip()
            if not title:
                continue
            if not self._matches_minecraft_title(title):
                continue

            # Ignore invisible zero-sized helper windows when dimensions exist
            width = getattr(win, "width", 1)
            height = getattr(win, "height", 1)
            if width is not None and height is not None and (width <= 0 or height <= 0):
                continue

            matched.append(
                DetectedWindow(
                    title=title,
                    is_minimized=bool(getattr(win, "isMinimized", False)),
                    is_active=bool(getattr(win, "isActive", False)),
                    handle=getattr(win, "_hWnd", None),
                    native_window=win,
                )
            )

        # Prefer active/non-minimized windows and titles containing Minecraft/SonOyuncu first
        matched.sort(key=self._window_priority, reverse=True)
        return matched

    def find_target_window(self, preferred_title: str = "") -> DetectedWindow | None:
        """Find the preferred Minecraft window or auto-pick the best match."""
        windows = self.list_minecraft_windows()
        if not windows:
            return None

        if preferred_title:
            pref_lower = preferred_title.strip().lower()
            for win in windows:
                if win.title.lower() == pref_lower:
                    return win
            for win in windows:
                if pref_lower in win.title.lower():
                    return win

        return windows[0]

    def inspect_status(self, preferred_title: str = "") -> tuple[WindowStatus, DetectedWindow | None]:
        """Return current WindowStatus and matching DetectedWindow if present."""
        if not self.is_available():
            return WindowStatus.UNAVAILABLE, None

        target = self.find_target_window(preferred_title=preferred_title)
        if target is None:
            return WindowStatus.NOT_FOUND, None

        return target.status, target

    def ensure_ready(
        self,
        preferred_title: str = "",
        auto_focus: bool = True,
        pause_if_minimized: bool = False,
        focus_delay: float = 0.25,
    ) -> tuple[bool, WindowStatus, str, DetectedWindow | None]:
        """Verify target Minecraft window exists and prepare it for chat input."""
        status, target = self.inspect_status(preferred_title=preferred_title)
        if status == WindowStatus.UNAVAILABLE:
            return False, status, "Pencere algılama modülü bu sistemde kullanılamıyor.", None
        if status == WindowStatus.NOT_FOUND or target is None:
            return False, WindowStatus.NOT_FOUND, "Minecraft penceresi bulunamadı veya kapatıldı.", None

        if target.is_minimized:
            if pause_if_minimized:
                return False, WindowStatus.MINIMIZED, "Minecraft penceresi simge durumuna küçültüldü.", target
            if not auto_focus:
                return (
                    False,
                    WindowStatus.MINIMIZED,
                    "Minecraft penceresi simge durumunda (otomatik odaklama kapalı).",
                    target,
                )
            if not self._activate_window(target):
                return False, WindowStatus.MINIMIZED, "Minecraft penceresi geri yüklenemedi.", target
            time.sleep(max(0.1, focus_delay))

        elif not target.is_active:
            if not auto_focus:
                return (
                    False,
                    WindowStatus.UNFOCUSED,
                    "Minecraft penceresi odakta değil (otomatik odaklama kapalı).",
                    target,
                )
            if not self._activate_window(target):
                return False, WindowStatus.UNFOCUSED, "Minecraft penceresi öne getirilemedi.", target
            time.sleep(max(0.05, focus_delay))

        # Re-verify window still exists after activation
        post_status, refreshed = self.inspect_status(preferred_title=target.title)
        if post_status == WindowStatus.NOT_FOUND or refreshed is None:
            return False, WindowStatus.NOT_FOUND, "Minecraft penceresi işlem sırasında kapandı.", None
        if post_status == WindowStatus.MINIMIZED:
            return False, WindowStatus.MINIMIZED, "Minecraft penceresi hâlâ simge durumunda.", refreshed

        return True, WindowStatus.READY, f"Hedef pencere hazır: {refreshed.title}", refreshed

    def _activate_window(self, window: DetectedWindow) -> bool:
        native = window.native_window
        if native is None:
            return False

        try:
            if window.is_minimized and hasattr(native, "restore"):
                native.restore()
                time.sleep(0.12)

            if hasattr(native, "activate"):
                native.activate()
            return True
        except Exception as exc:
            # Known PyGetWindow Windows quirk: raises exception with Windows error code 0 on success
            msg = str(exc)
            if "Error code from Windows: 0" in msg or "completed successfully" in msg.lower():
                return True

            logger.warning("PyGetWindow activate başarısız (%s), Win32 fallback deneniyor.", exc)
            return self._win32_focus_fallback(window.handle)

    @staticmethod
    def _win32_focus_fallback(hwnd: Any) -> bool:
        if sys.platform != "win32" or not hwnd:
            return False
        try:
            user32 = ctypes.windll.user32
            sw_restore = 9
            if user32.IsIconic(hwnd):
                user32.ShowWindow(hwnd, sw_restore)
            user32.SetForegroundWindow(hwnd)
            return True
        except Exception as exc:
            logger.error("Win32 pencere odaklama hatası: %s", exc)
            return False

    def _matches_minecraft_title(self, title: str) -> bool:
        lowered = title.lower()
        for excluded in self.excluded_keywords:
            if excluded.lower() in lowered:
                return False
        return any(keyword.lower() in lowered for keyword in self.keywords)

    @staticmethod
    def _window_priority(win: DetectedWindow) -> tuple[int, int, int]:
        title_l = win.title.lower()
        is_exact_mc = 1 if ("minecraft" in title_l or "sonoyuncu" in title_l) else 0
        not_launcher = 0 if "launcher" in title_l else 1
        active_score = 2 if win.is_active else (0 if win.is_minimized else 1)
        return (not_launcher, is_exact_mc, active_score)
