"""Optional Telegram notifications through YOUR OWN bot (BotFather). Never fatal."""
from __future__ import annotations

import os

import requests


def telegram(text: str) -> bool:
    token, chat = os.environ.get("TELEGRAM_BOT_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat:
        return False
    try:
        for i in range(0, len(text), 3900):
            requests.post(f"https://api.telegram.org/bot{token}/sendMessage",
                          json={"chat_id": chat, "text": text[i:i + 3900], "disable_web_page_preview": True},
                          timeout=15)
        return True
    except requests.RequestException:
        return False
