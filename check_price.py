"""
Simple Ticketmaster price monitor.
Checks the event's lowest price via Ticketmaster's free Discovery API,
and sends a notification (email + Telegram) whenever:
  - the price hits $0.00, OR
  - the price drops below the last price we already notified about.

All secrets are read from environment variables (set as GitHub Actions secrets).
"""

import os
import json
import requests
import smtplib
from email.mime.text import MIMEText

# ---- Config ----
EVENT_ID = "10006496902A8B6C"  # taken from your Ticketmaster URL
EVENT_URL = "https://www.ticketmaster.ca/fifa-fan-festival-toronto-toronto-ontario-07-04-2026/event/10006496902A8B6C"
STATE_FILE = "state.json"

TM_API_KEY = os.environ.get("TM_API_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
GMAIL_USER = os.environ.get("GMAIL_USER")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD")
NOTIFY_EMAIL = os.environ.get("NOTIFY_EMAIL")


def get_price():
    """Ask Ticketmaster's official API for the current price range."""
    url = f"https://app.ticketmaster.com/discovery/v2/events/{EVENT_ID}.json"
    resp = requests.get(url, params={"apikey": TM_API_KEY}, timeout=20)
    resp.raise_for_status()
    data = resp.json()
    price_ranges = data.get("priceRanges", [])
    if not price_ranges:
        return None, None
    min_price = min(p["min"] for p in price_ranges)
    currency = price_ranges[0].get("currency", "CAD")
    return min_price, currency


def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"lowest_notified": None}


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)


def send_email(subject, body):
    if not (GMAIL_USER and GMAIL_APP_PASSWORD and NOTIFY_EMAIL):
        print("Email not configured, skipping.")
        return
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = GMAIL_USER
    msg["To"] = NOTIFY_EMAIL
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        server.sendmail(GMAIL_USER, [NOTIFY_EMAIL], msg.as_string())
    print("Email sent.")


def send_telegram(text):
    if not (TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID):
        print("Telegram not configured, skipping.")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    r = requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": text}, timeout=20)
    print("Telegram response:", r.status_code)


def main():
    if not TM_API_KEY:
        raise SystemExit("Missing TM_API_KEY environment variable / secret.")

    min_price, currency = get_price()

    if min_price is None:
        print("No price data available right now (tickets may not be on sale yet).")
        return

    state = load_state()
    last_notified = state.get("lowest_notified")
    print(f"Current lowest price: {min_price} {currency} (last notified: {last_notified})")

    should_notify = False
    if min_price == 0:
        should_notify = last_notified != 0
    elif last_notified is None or min_price < last_notified:
        should_notify = True

    if should_notify:
        subject = f"Ticket price alert: now {min_price} {currency}"
        body = (
            f"The lowest available price for the FIFA Fan Festival Toronto event "
            f"is now {min_price} {currency}.\n\n{EVENT_URL}"
        )
        send_email(subject, body)
        send_telegram(f"{subject}\n{body}")
        state["lowest_notified"] = min_price
        save_state(state)
    else:
        print("No notification needed this run.")


if __name__ == "__main__":
    main()
