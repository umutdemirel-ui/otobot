"""Entry point for SonOyuncu Auto Message Bot."""

from __future__ import annotations

import ctypes
import logging
import sys

from app.utils import setup_logging


def _enable_windows_dpi_awareness() -> None:
    if sys.platform != "win32":
        return
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def main() -> int:
    logger = setup_logging(logging.INFO)
    _enable_windows_dpi_awareness()

    try:
        from app.ui.main_window import MainWindow

        app = MainWindow()
        app.mainloop()
        return 0
    except Exception as exc:
        logger.exception("Uygulama başlatılırken kritik hata oluştu")
        if sys.platform == "win32":
            try:
                ctypes.windll.user32.MessageBoxW(
                    0,
                    f"Uygulama başlatılamadı:\n{exc}",
                    "SonOyuncu Auto Message Bot - Hata",
                    0x10,
                )
            except Exception:
                pass
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
