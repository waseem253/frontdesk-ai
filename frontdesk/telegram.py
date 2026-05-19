"""Real Telegram integration.

A booking confirmation is delivered to Telegram via the Business-style
bot. Anyone who opens the bot and taps Start is registered, so the
confirmation lands in a real chat (this is the live proof of the
"Telegram Integration" requirement). Without a token it dry-run logs,
so the demo still works end to end.
"""
from __future__ import annotations

import os

import httpx

from .store import register_chat, telegram_chats


def _token() -> str | None:
    return os.environ.get("TELEGRAM_BOT_TOKEN")


def _api(method: str) -> str:
    return f"https://api.telegram.org/bot{_token()}/{method}"


def handle_update(update: dict) -> None:
    """Telegram webhook payload — register the chat, greet on /start."""
    msg = update.get("message") or update.get("edited_message") or {}
    chat = msg.get("chat") or {}
    chat_id = chat.get("id")
    if not chat_id:
        return
    register_chat(int(chat_id))
    text = (msg.get("text") or "").strip()
    if text.startswith("/start"):
        send_to(
            int(chat_id),
            "You're connected to FrontDesk. Run a booking in the web demo "
            "and the confirmation will arrive right here.",
        )


def send_to(chat_id: int, text: str) -> bool:
    if not _token():
        print(f"[telegram:dry-run -> {chat_id}] {text}")
        return True
    try:
        r = httpx.post(_api("sendMessage"),
                        json={"chat_id": chat_id, "text": text}, timeout=10)
        return r.is_success
    except Exception:
        return False


def broadcast_booking(summary: str) -> dict:
    """Send to the owner chat if configured, else everyone who /start-ed."""
    owner = os.environ.get("TELEGRAM_OWNER_CHAT_ID")
    targets = [int(owner)] if owner else telegram_chats()
    if not _token():
        print(f"[telegram:dry-run broadcast] {summary}")
        return {"via": "dry-run", "delivered": 0}
    delivered = sum(1 for c in targets if send_to(c, summary))
    return {"via": "telegram", "delivered": delivered, "targets": len(targets)}


def set_webhook(base_url: str) -> dict:
    if not _token():
        return {"ok": False, "reason": "no token"}
    r = httpx.post(_api("setWebhook"),
                   json={"url": f"{base_url}/telegram/webhook"}, timeout=10)
    return r.json()
