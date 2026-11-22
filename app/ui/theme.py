"""Modern dark theme tokens and typography helpers for CustomTkinter."""

from __future__ import annotations

import sys

COLORS = {
    "bg_app": "#0D1117",
    "bg_card": "#161B22",
    "bg_card_alt": "#1C222B",
    "bg_input": "#0F141B",
    "border": "#2A313C",
    "border_subtle": "#21262D",
    "text_primary": "#F0F6FC",
    "text_secondary": "#9CA3AF",
    "text_muted": "#6E7681",
    "accent": "#22C55E",
    "accent_hover": "#16A34A",
    "warning": "#F59E0B",
    "warning_hover": "#D97706",
    "danger": "#EF4444",
    "danger_hover": "#DC2626",
    "info": "#3B82F6",
    "info_hover": "#2563EB",
    "neutral_btn": "#262D38",
    "neutral_btn_hover": "#323B49",
    "badge_idle_bg": "#21262D",
    "badge_running_bg": "#133924",
    "badge_paused_bg": "#3A2B12",
    "badge_danger_bg": "#3E181B",
}

FONT_FAMILY = "Segoe UI" if sys.platform == "win32" else "DejaVu Sans"
MONO_FONT_FAMILY = "Consolas" if sys.platform == "win32" else "DejaVu Sans Mono"


def font_spec(size: int = 13, weight: str = "normal", mono: bool = False) -> tuple[str, int, str]:
    """Return a Tkinter/CustomTkinter-safe font tuple."""
    family = MONO_FONT_FAMILY if mono else FONT_FAMILY
    return (family, size, weight)
