# -*- coding: utf-8 -*-
from __future__ import annotations
import json
import os
import urllib.request
from typing import Optional

from .base import Notifier


class TelegramNotifier(Notifier):
    def __init__(self, token: Optional[str] = None, chat_id: Optional[str] = None):
        self.token = token or os.environ.get("TELEGRAM_BOT_TOKEN") or ""
        self.chat_id = chat_id or os.environ.get("TELEGRAM_CHAT_ID") or ""

    def enabled(self) -> bool:
        if os.environ.get("NOTIFY_ENABLED", "true").lower() in ("0", "false", "no"):
            return False
        return bool(self.token and self.chat_id)

    def send(self, title: str, message: str, level: str = "info") -> bool:
        if not self.enabled():
            return False
        try:
            text = f"*{title}*\n{message}"
            url = f"https://api.telegram.org/bot{self.token}/sendMessage"
            payload = {"chat_id": self.chat_id, "text": text, "parse_mode": "Markdown"}
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(req, timeout=10) as resp:
                return resp.status == 200
        except Exception:
            return False
