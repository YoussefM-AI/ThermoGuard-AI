"""
ThermoGuard AI - Notification Dispatcher
Sends real-time alerts via Telegram bot when CRITICAL events are triggered.

Setup:
  1. Create a Telegram bot via @BotFather → get TELEGRAM_BOT_TOKEN
  2. Message your bot or use @userinfobot → get your TELEGRAM_CHAT_ID
  3. Set both as environment variables in Render (or .env locally)

No token = notifications silently disabled (zero crash risk).
"""

import os
import threading
from datetime import UTC, datetime
from urllib.request import Request, urlopen
from urllib.error import URLError
import json

# ── Config ────────────────────────────────────────────────────────────────────
_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
_CHAT_ID   = os.getenv("TELEGRAM_CHAT_ID", "")

# Only fire Telegram for these severities (WARNING can be noisy on simulation)
_NOTIFY_SEVERITIES = {"CRITICAL"}


def _is_configured() -> bool:
    return bool(_BOT_TOKEN and _CHAT_ID)


def _send_telegram(text: str) -> bool:
    """
    Fires a Telegram message via Bot API (pure stdlib — no extra deps).
    Returns True on success, False on any network/API error.
    """
    if not _is_configured():
        return False

    url = f"https://api.telegram.org/bot{_BOT_TOKEN}/sendMessage"
    payload = json.dumps({
        "chat_id": _CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }).encode("utf-8")

    req = Request(url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urlopen(req, timeout=8) as resp:
            return resp.status == 200
    except (URLError, OSError):
        return False


def _build_message(severity: str, message: str, temperature: float | None, humidity: float | None, anomaly_score: float | None) -> str:
    """Builds a nicely formatted Telegram alert message."""
    icon = "🔴" if severity == "CRITICAL" else "🟡"
    ts   = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")

    lines = [
        f"{icon} <b>ThermoGuard AI — {severity} ALERT</b>",
        f"📅 <code>{ts}</code>",
        "",
        f"📋 {message}",
    ]

    if temperature is not None:
        lines.append(f"🌡️  Temperature: <b>{temperature:.1f}°C</b>")
    if humidity is not None:
        lines.append(f"💧 Humidity:    <b>{humidity:.1f}%</b>")
    if anomaly_score is not None:
        lines.append(f"🤖 AI Score:    <code>{anomaly_score:.4f}</code>")

    lines += ["", "⚡ Check your ThermoGuard dashboard immediately."]
    return "\n".join(lines)


def dispatch_alert(
    severity: str,
    message: str,
    temperature: float | None = None,
    humidity: float | None = None,
    anomaly_score: float | None = None,
) -> None:
    """
    Public interface. Called by services.py after an alert is inserted.
    - Skips severities not in _NOTIFY_SEVERITIES (WARNING spam prevention).
    - Runs in a background daemon thread so it never blocks the API response.
    - Silently swallows all errors — notifications are best-effort.
    """
    if severity.upper() not in _NOTIFY_SEVERITIES:
        return
    if not _is_configured():
        return

    text = _build_message(severity, message, temperature, humidity, anomaly_score)

    def _fire():
        try:
            _send_telegram(text)
        except Exception:
            pass  # Never crash the app over a notification failure

    t = threading.Thread(target=_fire, daemon=True, name="telegram-notify")
    t.start()
