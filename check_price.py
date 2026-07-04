"""
Ticketmaster price monitor - keyword/search based.

Instead of watching a single hardcoded event ID (each date of a recurring
event like a festival has its own separate ID, and IDs from the public URL
don't always match the Discovery API's internal ID), this version searches
by keyword every run and checks EVERY upcoming date it finds.

It notifies (email + Telegram) for any date where:
  - the price hits $0.00, OR
  - the price drops below the last price we already notified about for that date

State (what we've already notified about, per event date) is stored in state.json.
"""

import os
import json
import requests
import smtplib
from email.mime.text import MIMEText

# ---- Config ----
KEYWORD = "FIFA Fan Festival Toronto"
STATE_FILE = "state.json"

TM_API_KEY = os.environ.get("TM_API_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
GMAIL_USER = os.environ.get("GMAIL_USER")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD")
NOTIFY_EMAIL = os.environ.get("NOTIFY_EMAIL")


def search_events():
    """Search Ticketmaster for all upcoming events matching the keyword."""
    url = "https://app.ticketmaster.com/discovery/v2/events.json"
    params = {"apikey": TM_API_KEY, "keyword": KEYWORD, "size": 50}
    resp = requests.get(url, params=params, timeout=20)
    resp.raise_for_status()
    data = resp.json()
    return data.get("_embedded", {}).get("events", [])


def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            content = f.read().strip()
            return json.loads(content) if content else {}
    return {}


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


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

    events = search_events()
    print(f"Found {len(events)} matching events.")

    state = load_state()  # dict: {event_id: last_notified_price}

    for ev in events:
        event_id = ev.get("id")
        name = ev.get("name", KEYWORD)
        date = ev.get("dates", {}).get("start", {}).get("localDate", "unknown date")
        event_url = ev.get("url", "")
        price_ranges = ev.get("priceRanges", [])

        if not price_ranges:
            print(f"{date} ({event_id}): no price data yet.")
            continue

        min_price = min(p["min"] for p in price_ranges)
        currency = price_ranges[0].get("currency", "CAD")
        last_notified = state.get(event_id)

        print(f"{date} ({event_id}): lowest price {min_price} {currency} (last notified: {last_notified})")

        should_notify = False
        if min_price == 0:
            should_notify = last_notified != 0
        elif last_notified is None or min_price < last_notified:
            should_notify = True

        if should_notify:
            subject = f"Ticket price alert: {name} {date} now {min_price} {currency}"
            body = f"{name}\nDate: {date}\nLowest price: {min_price} {currency}\n\n{event_url}"
            send_email(subject, body)
            send_telegram(f"{subject}\n{body}")
            state[event_id] = min_price

    save_state(state)


if __name__ == "__main__":
    main()
