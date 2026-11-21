"""Phone notifications. Never fatal. Channels are switched on by env vars in .env:

ntfy (recommended):  NTFY_TOPIC=<long random name>   [NTFY_URL=https://ntfy.sh]  [NTFY_TOKEN=...]
Telegram:            TELEGRAM_BOT_TOKEN=...  TELEGRAM_CHAT_ID=...
"""
from __future__ import annotations

import os

import requests


def _ntfy(text: str, title: str, priority: str, tags: str) -> bool:
    topic = os.environ.get("NTFY_TOPIC")
    if not topic:
        return False
    url = os.environ.get("NTFY_URL", "https://ntfy.sh").rstrip("/") + "/" + topic
    headers = {"Title": title.encode("utf-8"), "Priority": priority, "Tags": tags}
    if os.environ.get("NTFY_TOKEN"):
        headers["Authorization"] = f"Bearer {os.environ['NTFY_TOKEN']}"
    try:
        body = text.encode("utf-8")
        for i in range(0, max(len(body), 1), 3800):  # ntfy caps a message at 4 KB
            requests.post(url, data=body[i:i + 3800], headers=headers, timeout=15)
        return True
    except requests.RequestException:
        return False


def _telegram(text: str) -> bool:
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


def send(text: str, title: str = "Nirvana", urgent: bool = False) -> bool:
    """Send to every configured channel. urgent = high priority (stops, failures)."""
    a = _ntfy(text, title, "high" if urgent else "default", "rotating_light" if urgent else "chart_with_upwards_trend")
    b = _telegram(f"{title}\n{text}" if title != "Nirvana" else text)
    return a or b


telegram = send  # backwards compatibility
