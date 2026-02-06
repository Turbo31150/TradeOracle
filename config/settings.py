"""TradeOracle Configuration - Loads from .env"""
import os
from dotenv import load_dotenv

load_dotenv()

# Gemini 3
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
GEMINI_THINKING_MODEL = os.getenv("GEMINI_THINKING_MODEL", "gemini-2.5-pro")

# MEXC Futures API
MEXC_ACCESS_KEY = os.getenv("MEXC_ACCESS_KEY", "")
MEXC_SECRET_KEY = os.getenv("MEXC_SECRET_KEY", "")
MEXC_TICKER_URL = "https://contract.mexc.com/api/v1/contract/ticker"
MEXC_KLINE_URL = "https://contract.mexc.com/api/v1/contract/kline"
MEXC_DEPTH_URL = "https://contract.mexc.com/api/v1/contract/depth"

# Telegram
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# Trading Parameters
TRADING_CONFIG = {
    "default_leverage": 10,
    "default_size_usdt": 10,
    "tp1_percent": 1.5,
    "tp2_percent": 3.0,
    "tp3_percent": 5.5,
    "sl_percent": 1.2,
    "max_positions": 10,
}

# Scanner Parameters
SCANNER_CONFIG = {
    "min_score": 70,
    "min_volume_24h": 100000,
    "max_signals": 15,
}

# Database
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "database", "tradeoracle.db")
