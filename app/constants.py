"""Application constants, enumerations, and default configuration values."""

from __future__ import annotations

from enum import Enum

APP_TITLE = "SonOyuncu Auto Message Bot"
APP_VERSION = "1.0.0"
APP_SUBTITLE = "Minecraft Java Edition • Skyblock Sohbet Asistanı"

DEFAULT_INTERVAL_SECONDS = 120
MIN_INTERVAL_SECONDS = 5
RECOMMENDED_MIN_INTERVAL_SECONDS = 60
MAX_INTERVAL_SECONDS = 86400

DEFAULT_INITIAL_DELAY_SECONDS = 3
DEFAULT_CHAT_OPEN_DELAY = 0.30
DEFAULT_PRE_SEND_FOCUS_DELAY = 0.25
DEFAULT_POST_PASTE_DELAY = 0.10

MINECRAFT_MAX_CHAT_LENGTH = 256
SONOYUNCU_SAFE_CHAT_LENGTH = 100

DEFAULT_WINDOW_KEYWORDS = [
    "SonOyuncu",
    "Minecraft",
    "LWJGL",
]

EXCLUDED_WINDOW_KEYWORDS = [
    "SonOyuncu Auto Message Bot",
    "Auto Message Bot",
]

DEFAULT_CHAT_KEY = "t"
SUPPORTED_CHAT_KEYS = ["t", "enter", "/"]
SUPPORTED_INPUT_METHODS = ["clipboard", "typing"]

EMERGENCY_STOP_KEY = "F8"

RULES_COMPLIANCE_TEXT = (
    "Bu araç yalnızca kullanıcının kendi belirlediği duyuru/reklam mesajlarını "
    "standart klavye girişi ile Minecraft sohbetine göndermesine yardımcı olur.\n\n"
    "• CAPTCHA veya anti-cheat sistemlerini aşmaya yönelik hiçbir özellik içermez.\n"
    "• SonOyuncu sunucusunun reklam süresi ve spam kurallarına uymak kullanıcının sorumluluğundadır "
    "(önerilen aralık: en az 120 saniye).\n"
    "• Acil durdurma için istediğiniz zaman F8 tuşuna basabilirsiniz."
)


class BotState(str, Enum):
    """Lifecycle states of the auto-message worker."""

    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"

    @property
    def label_tr(self) -> str:
        mapping = {
            BotState.IDLE: "Hazır / Durduruldu",
            BotState.RUNNING: "Çalışıyor",
            BotState.PAUSED: "Duraklatıldı",
            BotState.STOPPING: "Durduruluyor...",
        }
        return mapping[self]


class WindowStatus(str, Enum):
    """Status of the target Minecraft Java Edition window."""

    READY = "ready"
    MINIMIZED = "minimized"
    UNFOCUSED = "unfocused"
    NOT_FOUND = "not_found"
    UNAVAILABLE = "unavailable"

    @property
    def label_tr(self) -> str:
        mapping = {
            WindowStatus.READY: "Bağlı ve Odakta (Hazır)",
            WindowStatus.MINIMIZED: "Bulundu (Simge Durumunda)",
            WindowStatus.UNFOCUSED: "Bulundu (Arka Planda)",
            WindowStatus.NOT_FOUND: "Minecraft Penceresi Bulunamadı",
            WindowStatus.UNAVAILABLE: "Pencere Algılama Kullanılamıyor",
        }
        return mapping[self]
