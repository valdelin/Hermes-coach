# -*- coding: utf-8 -*-
from __future__ import annotations
import os

from .base import Notifier, NullNotifier
from .telegram import TelegramNotifier


def get_notifier() -> Notifier:
    try:
        if os.environ.get("TELEGRAM_BOT_TOKEN") and os.environ.get("TELEGRAM_CHAT_ID"):
            n = TelegramNotifier()
            if n.enabled():
                return n
    except Exception:
        pass
    return NullNotifier()
