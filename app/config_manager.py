"""JSON configuration and message list persistence manager."""

from __future__ import annotations

import json
import logging
import os
import shutil
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from app.constants import (
    DEFAULT_CHAT_KEY,
    DEFAULT_CHAT_OPEN_DELAY,
    DEFAULT_INITIAL_DELAY_SECONDS,
    DEFAULT_INTERVAL_SECONDS,
    DEFAULT_POST_PASTE_DELAY,
    DEFAULT_PRE_SEND_FOCUS_DELAY,
    DEFAULT_WINDOW_KEYWORDS,
    EMERGENCY_STOP_KEY,
    MAX_INTERVAL_SECONDS,
    MIN_INTERVAL_SECONDS,
    SUPPORTED_CHAT_KEYS,
    SUPPORTED_INPUT_METHODS,
)
from app.utils import get_settings_path

logger = logging.getLogger("otobot.config")


@dataclass
class MessageItem:
    """Single chat message entry with ordering and active flag."""

    text: str
    enabled: bool = True
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MessageItem":
        text = str(data.get("text", "")).strip()
        enabled = bool(data.get("enabled", True))
        item_id = str(data.get("id") or uuid.uuid4().hex[:12])
        return cls(id=item_id, text=text, enabled=enabled)


@dataclass
class TimingSettings:
    """Timing configuration for message intervals and input delays."""

    interval_seconds: int = DEFAULT_INTERVAL_SECONDS
    send_first_immediately: bool = True
    initial_delay_seconds: int = DEFAULT_INITIAL_DELAY_SECONDS
    chat_open_delay: float = DEFAULT_CHAT_OPEN_DELAY
    pre_send_focus_delay: float = DEFAULT_PRE_SEND_FOCUS_DELAY
    post_paste_delay: float = DEFAULT_POST_PASTE_DELAY

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TimingSettings":
        interval = _clamp_int(
            data.get("interval_seconds", DEFAULT_INTERVAL_SECONDS),
            MIN_INTERVAL_SECONDS,
            MAX_INTERVAL_SECONDS,
            DEFAULT_INTERVAL_SECONDS,
        )
        initial_delay = _clamp_int(
            data.get("initial_delay_seconds", DEFAULT_INITIAL_DELAY_SECONDS),
            1,
            30,
            DEFAULT_INITIAL_DELAY_SECONDS,
        )
        chat_open_delay = _clamp_float(
            data.get("chat_open_delay", DEFAULT_CHAT_OPEN_DELAY),
            0.05,
            2.0,
            DEFAULT_CHAT_OPEN_DELAY,
        )
        pre_send_focus_delay = _clamp_float(
            data.get("pre_send_focus_delay", DEFAULT_PRE_SEND_FOCUS_DELAY),
            0.05,
            2.0,
            DEFAULT_PRE_SEND_FOCUS_DELAY,
        )
        post_paste_delay = _clamp_float(
            data.get("post_paste_delay", DEFAULT_POST_PASTE_DELAY),
            0.02,
            1.5,
            DEFAULT_POST_PASTE_DELAY,
        )
        return cls(
            interval_seconds=interval,
            send_first_immediately=bool(data.get("send_first_immediately", True)),
            initial_delay_seconds=initial_delay,
            chat_open_delay=chat_open_delay,
            pre_send_focus_delay=pre_send_focus_delay,
            post_paste_delay=post_paste_delay,
        )


@dataclass
class MinecraftSettings:
    """Minecraft window detection and chat input preferences."""

    window_keywords: list[str] = field(default_factory=lambda: list(DEFAULT_WINDOW_KEYWORDS))
    preferred_window_title: str = ""
    auto_focus_before_send: bool = True
    pause_if_minimized: bool = False
    chat_key: str = DEFAULT_CHAT_KEY
    input_method: str = "clipboard"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MinecraftSettings":
        raw_keywords = data.get("window_keywords", DEFAULT_WINDOW_KEYWORDS)
        if isinstance(raw_keywords, list):
            keywords = [str(k).strip() for k in raw_keywords if str(k).strip()]
        else:
            keywords = list(DEFAULT_WINDOW_KEYWORDS)
        if not keywords:
            keywords = list(DEFAULT_WINDOW_KEYWORDS)

        chat_key = str(data.get("chat_key", DEFAULT_CHAT_KEY)).strip().lower()
        if chat_key not in SUPPORTED_CHAT_KEYS:
            chat_key = DEFAULT_CHAT_KEY

        input_method = str(data.get("input_method", "clipboard")).strip().lower()
        if input_method not in SUPPORTED_INPUT_METHODS:
            input_method = "clipboard"

        return cls(
            window_keywords=keywords,
            preferred_window_title=str(data.get("preferred_window_title", "")).strip(),
            auto_focus_before_send=bool(data.get("auto_focus_before_send", True)),
            pause_if_minimized=bool(data.get("pause_if_minimized", False)),
            chat_key=chat_key,
            input_method=input_method,
        )


@dataclass
class SafetySettings:
    """Safety and rule-compliance settings."""

    rules_accepted: bool = False
    emergency_stop_key: str = EMERGENCY_STOP_KEY
    restore_clipboard: bool = True

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SafetySettings":
        return cls(
            rules_accepted=bool(data.get("rules_accepted", False)),
            emergency_stop_key=str(data.get("emergency_stop_key", EMERGENCY_STOP_KEY)),
            restore_clipboard=bool(data.get("restore_clipboard", True)),
        )


@dataclass
class AppConfig:
    """Root application configuration structure."""

    version: int = 1
    messages: list[MessageItem] = field(default_factory=list)
    timing: TimingSettings = field(default_factory=TimingSettings)
    minecraft: MinecraftSettings = field(default_factory=MinecraftSettings)
    safety: SafetySettings = field(default_factory=SafetySettings)

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "messages": [asdict(item) for item in self.messages],
            "timing": asdict(self.timing),
            "minecraft": asdict(self.minecraft),
            "safety": asdict(self.safety),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AppConfig":
        raw_messages = data.get("messages", [])
        messages: list[MessageItem] = []
        if isinstance(raw_messages, list):
            for entry in raw_messages:
                if isinstance(entry, dict):
                    item = MessageItem.from_dict(entry)
                    if item.text:
                        messages.append(item)

        timing_raw = data.get("timing", {})
        minecraft_raw = data.get("minecraft", {})
        safety_raw = data.get("safety", {})

        return cls(
            version=int(data.get("version", 1)),
            messages=messages,
            timing=TimingSettings.from_dict(timing_raw if isinstance(timing_raw, dict) else {}),
            minecraft=MinecraftSettings.from_dict(
                minecraft_raw if isinstance(minecraft_raw, dict) else {}
            ),
            safety=SafetySettings.from_dict(safety_raw if isinstance(safety_raw, dict) else {}),
        )


class ConfigManager:
    """Loads, validates, mutates, and persists AppConfig to JSON."""

    def __init__(self, settings_path: Path | None = None) -> None:
        self.settings_path = settings_path or get_settings_path()
        self.config: AppConfig = self.load()

    def load(self) -> AppConfig:
        """Load configuration from disk, creating defaults if missing or corrupted."""
        if not self.settings_path.exists():
            logger.info("Ayar dosyası bulunamadı, varsayılan ayarlar oluşturuluyor: %s", self.settings_path)
            config = self._default_config()
            self.config = config
            self.save(config)
            return config

        try:
            raw_text = self.settings_path.read_text(encoding="utf-8")
            parsed = json.loads(raw_text)
            if not isinstance(parsed, dict):
                raise ValueError("Kök JSON nesne (dict) değil")
            config = AppConfig.from_dict(parsed)
            self.config = config
            return config
        except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
            logger.error("Ayar dosyası okunamadı (%s). Yedek alınıp varsayılana dönülüyor.", exc)
            self._backup_corrupted_file()
            config = self._default_config()
            self.config = config
            self.save(config)
            return config

    def save(self, config: AppConfig | None = None) -> bool:
        """Persist configuration atomically to JSON."""
        target = config or self.config
        self.config = target
        try:
            self.settings_path.parent.mkdir(parents=True, exist_ok=True)
            temp_path = self.settings_path.with_suffix(".json.tmp")
            payload = json.dumps(target.to_dict(), ensure_ascii=False, indent=2)
            temp_path.write_text(payload, encoding="utf-8")
            os.replace(temp_path, self.settings_path)
            return True
        except OSError as exc:
            logger.error("Ayarlar kaydedilirken hata oluştu: %s", exc)
            return False

    def _backup_corrupted_file(self) -> None:
        try:
            if self.settings_path.exists():
                backup_path = self.settings_path.with_suffix(".json.bak")
                shutil.copy2(self.settings_path, backup_path)
        except OSError:
            pass

    @staticmethod
    def _default_config() -> AppConfig:
        return AppConfig(
            messages=[],
            timing=TimingSettings(),
            minecraft=MinecraftSettings(),
            safety=SafetySettings(),
        )

    # --- Message management helpers ---

    def add_message(self, text: str, enabled: bool = True) -> MessageItem:
        cleaned = text.strip()
        if not cleaned:
            raise ValueError("Mesaj metni boş olamaz.")
        item = MessageItem(text=cleaned, enabled=enabled)
        self.config.messages.append(item)
        self.save()
        return item

    def update_message(self, message_id: str, new_text: str, enabled: bool | None = None) -> MessageItem:
        cleaned = new_text.strip()
        if not cleaned:
            raise ValueError("Mesaj metni boş olamaz.")
        for item in self.config.messages:
            if item.id == message_id:
                item.text = cleaned
                if enabled is not None:
                    item.enabled = enabled
                self.save()
                return item
        raise KeyError(f"Mesaj bulunamadı: {message_id}")

    def delete_message(self, message_id: str) -> bool:
        before = len(self.config.messages)
        self.config.messages = [m for m in self.config.messages if m.id != message_id]
        if len(self.config.messages) != before:
            self.save()
            return True
        return False

    def toggle_message(self, message_id: str, enabled: bool) -> bool:
        for item in self.config.messages:
            if item.id == message_id:
                item.enabled = enabled
                self.save()
                return True
        return False

    def move_message(self, message_id: str, direction: int) -> bool:
        """Move message up (-1) or down (+1) in send order."""
        idx = next((i for i, m in enumerate(self.config.messages) if m.id == message_id), None)
        if idx is None:
            return False
        new_idx = idx + direction
        if not (0 <= new_idx < len(self.config.messages)):
            return False
        msgs = self.config.messages
        msgs[idx], msgs[new_idx] = msgs[new_idx], msgs[idx]
        self.save()
        return True

    def get_enabled_messages(self) -> list[MessageItem]:
        return [m for m in self.config.messages if m.enabled and m.text.strip()]


def _clamp_int(value: Any, low: int, high: int, default: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return max(low, min(high, parsed))


def _clamp_float(value: Any, low: float, high: float, default: float) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return default
    return max(low, min(high, parsed))
