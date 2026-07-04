"""
Standalone test - sends one test message to Telegram and email, unconditionally.
Use this to confirm your secrets and delivery channels work,
independent of the actual price-checking logic.
"""

import os
import requests
import smtplib
from email.mime.text import MIMEText

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
GMAIL_USER = os.environ.get("GMAIL_USER")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD")
NOTIFY_EMAIL = os.environ.get("NOTIFY_EMAIL")

MESSAGE = "✅ Test message from your Ticket Price Monitor. If you see this, notifications are working!"


def test_telegram():
    if not (TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID):
        print("Telegram secrets missing - skipped.")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    r = requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": MESSAGE}, timeout=20)
    print("Telegram status code:", r.status_code)
    print("Telegram response body:", r.text)


def test_email():
    if not (GMAIL_USER and GMAIL_APP_PASSWORD and NOTIFY_EMAIL):
        print("Email secrets missing - skipped.")
        return
    msg = MIMEText(MESSAGE)
    msg["Subject"] = "Test: Ticket Price Monitor"
    msg["From"] = GMAIL_USER
    msg["To"] = NOTIFY_EMAIL
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        server.sendmail(GMAIL_USER, [NOTIFY_EMAIL], msg.as_string())
    print("Email sent successfully.")


if __name__ == "__main__":
    test_telegram()
    test_email()
