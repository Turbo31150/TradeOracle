"""
TradeOracle - Telegram Alert Tools
Extracted from Trading MCP Ultimate v3.7
"""
import json
import urllib.request
import urllib.parse
from langchain_core.tools import tool

from config.settings import TELEGRAM_TOKEN, TELEGRAM_CHAT_ID


@tool
def send_telegram_alert(message: str) -> str:
    """Send a trading alert or notification via Telegram bot.
    Use this to notify the user about important trading signals or margin alerts.

    Args:
        message: The alert message to send. Can include HTML formatting.
    """
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        return "Telegram not configured. Set TELEGRAM_TOKEN and TELEGRAM_CHAT_ID in .env"

    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        data = urllib.parse.urlencode({
            'chat_id': TELEGRAM_CHAT_ID,
            'text': message,
            'parse_mode': 'HTML'
        }).encode()

        req = urllib.request.Request(url, data=data)
        with urllib.request.urlopen(req, timeout=10) as r:
            result = json.loads(r.read())

        if result.get('ok'):
            return f"Alert sent to Telegram successfully (message_id: {result['result']['message_id']})"
        else:
            return f"Telegram error: {result.get('description', 'Unknown error')}"
    except Exception as e:
        return f"Failed to send Telegram alert: {str(e)}"
