"""
ThermoGuard AI - Email Alert Dispatcher
Sends real-time email alerts when CRITICAL events are triggered.

Uses Python's built-in smtplib — zero extra dependencies.

Setup (set these in Render environment variables):
  ALERT_EMAIL_FROM      → sender address  (e.g. yourname@gmail.com)
  ALERT_EMAIL_TO        → recipient address (can be same as FROM)
  ALERT_EMAIL_PASSWORD  → Gmail App Password (NOT your normal password)
                          Gmail → Manage Account → Security → App Passwords
  SMTP_HOST             → (optional) defaults to smtp.gmail.com
  SMTP_PORT             → (optional) defaults to 587

For Gmail you MUST use an App Password (2FA required on the Google account).
For Outlook/Hotmail: SMTP_HOST=smtp-mail.outlook.com  SMTP_PORT=587
For Yahoo:           SMTP_HOST=smtp.mail.yahoo.com    SMTP_PORT=587

No config = email silently disabled (zero crash risk).
"""

import os
import smtplib
import threading
from datetime import UTC, datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# ── Config ────────────────────────────────────────────────────────────────────
_FROM     = os.getenv("ALERT_EMAIL_FROM", "")
_TO       = os.getenv("ALERT_EMAIL_TO", "")
_PASSWORD = os.getenv("ALERT_EMAIL_PASSWORD", "")
_HOST     = os.getenv("SMTP_HOST", "smtp.gmail.com")
_PORT     = int(os.getenv("SMTP_PORT", "587"))

# Only fire email for these severities (WARNING can be noisy during simulation)
_NOTIFY_SEVERITIES = {"CRITICAL"}


def _is_configured() -> bool:
    return bool(_FROM and _TO and _PASSWORD)


def _build_email(severity: str, message: str, temperature: float | None, humidity: float | None, anomaly_score: float | None) -> MIMEMultipart:
    """Builds a plain-text + HTML multipart email."""
    ts   = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
    icon = "🔴" if severity == "CRITICAL" else "🟡"
    subject = f"{icon} ThermoGuard AI — {severity} Alert"

    # ── Plain text fallback ──
    plain_lines = [
        f"ThermoGuard AI — {severity} ALERT",
        f"Time: {ts}",
        "",
        message,
    ]
    if temperature is not None:
        plain_lines.append(f"Temperature : {temperature:.1f} °C")
    if humidity is not None:
        plain_lines.append(f"Humidity    : {humidity:.1f} %")
    if anomaly_score is not None:
        plain_lines.append(f"AI Score    : {anomaly_score:.4f}")
    plain_lines += ["", "Check your ThermoGuard dashboard immediately."]

    # ── HTML version ──
    temp_str  = f"<tr><td>🌡️ Temperature</td><td><b>{temperature:.1f} °C</b></td></tr>" if temperature is not None else ""
    hum_str   = f"<tr><td>💧 Humidity</td><td><b>{humidity:.1f} %</b></td></tr>" if humidity is not None else ""
    score_str = f"<tr><td>🤖 AI Score</td><td><code>{anomaly_score:.4f}</code></td></tr>" if anomaly_score is not None else ""

    html = f"""
    <html><body style="font-family:Arial,sans-serif;background:#0F172A;color:#F8FAFC;padding:24px;">
      <div style="max-width:520px;margin:auto;background:#1E293B;border-radius:12px;padding:28px;border-left:5px solid #F43F5E;">
        <h2 style="color:#F43F5E;margin-top:0;">{icon} ThermoGuard AI — {severity} ALERT</h2>
        <p style="color:#94A3B8;font-size:13px;">📅 {ts}</p>
        <p style="color:#F8FAFC;">{message}</p>
        <table style="width:100%;border-collapse:collapse;margin-top:16px;">
          {temp_str}{hum_str}{score_str}
        </table>
        <hr style="border-color:#334155;margin:20px 0;">
        <p style="color:#64748B;font-size:12px;">
          ⚡ This alert was generated automatically by ThermoGuard AI.<br>
          Log in to your dashboard to acknowledge this alert.
        </p>
      </div>
    </body></html>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = f"ThermoGuard AI <{_FROM}>"
    msg["To"]      = _TO
    msg.attach(MIMEText("\n".join(plain_lines), "plain"))
    msg.attach(MIMEText(html, "html"))
    return msg


def _send_email(msg: MIMEMultipart) -> tuple[bool, str]:
    """Sends via SMTP TLS. Returns (success, error_detail)."""
    try:
        with smtplib.SMTP(_HOST, _PORT, timeout=10) as server:
            server.ehlo()
            server.starttls()
            server.login(_FROM, _PASSWORD)
            server.sendmail(_FROM, _TO, msg.as_string())
        return True, ""
    except smtplib.SMTPAuthenticationError as e:
        return False, f"Auth failed — wrong password or App Password not used: {e}"
    except smtplib.SMTPException as e:
        return False, f"SMTP error: {e}"
    except OSError as e:
        return False, f"Network error ({_HOST}:{_PORT}): {e}"


def send_test_email() -> dict:
    """
    Synchronously sends a test alert email and returns a result dict.
    Called by GET /api/notifications/test for quick diagnosis.
    """
    if not _is_configured():
        missing = [k for k, v in {
            "ALERT_EMAIL_FROM": _FROM,
            "ALERT_EMAIL_TO": _TO,
            "ALERT_EMAIL_PASSWORD": _PASSWORD,
        }.items() if not v]
        return {"ok": False, "error": f"Missing environment variables: {', '.join(missing)}"}

    msg = _build_email(
        severity="CRITICAL",
        message="✅ This is a ThermoGuard AI test email. If you received this, alerts are working!",
        temperature=55.3,
        humidity=87.1,
        anomaly_score=-0.041,
    )
    ok, err = _send_email(msg)
    if ok:
        return {"ok": True, "message": f"Test email sent to {_TO}"}
    return {"ok": False, "error": err}


def dispatch_alert(
    severity: str,
    message: str,
    temperature: float | None = None,
    humidity: float | None = None,
    anomaly_score: float | None = None,
) -> None:
    """
    Public interface. Called by services.py after an alert is inserted.
    - Only sends for CRITICAL severity (WARNING skipped to avoid noise).
    - Runs in a background daemon thread — never blocks the API response.
    - Silently swallows all errors — notifications are best-effort.
    """
    if severity.upper() not in _NOTIFY_SEVERITIES:
        return
    if not _is_configured():
        return

    msg = _build_email(severity, message, temperature, humidity, anomaly_score)

    def _fire():
        try:
            ok, err = _send_email(msg)
            if not ok:
                # Visible in Render logs under "Logs" tab
                print(f"[ThermoGuard] Email alert FAILED: {err}", flush=True)
        except Exception as exc:
            print(f"[ThermoGuard] Email alert exception: {exc}", flush=True)

    t = threading.Thread(target=_fire, daemon=True, name="email-notify")
    t.start()
