"""
TradeOracle - Signal Database
SQLite storage for trading signals, decisions, and performance tracking
"""
import sqlite3
import json
from datetime import datetime
from typing import Dict, List, Optional

from config.settings import DB_PATH


def _get_connection():
    """Get SQLite connection with auto-creation"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    _init_tables(conn)
    return conn


def _init_tables(conn):
    """Initialize database tables"""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT DEFAULT (datetime('now')),
            symbol TEXT NOT NULL,
            direction TEXT NOT NULL,
            score INTEGER DEFAULT 0,
            price REAL,
            tp1 REAL,
            tp2 REAL,
            tp3 REAL,
            sl REAL,
            reasons TEXT,
            timeframe TEXT,
            confidence INTEGER,
            agent_reasoning TEXT,
            source TEXT DEFAULT 'tradeoracle'
        );

        CREATE TABLE IF NOT EXISTS decisions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT DEFAULT (datetime('now')),
            query TEXT,
            response TEXT,
            tools_used TEXT,
            model TEXT,
            duration_ms INTEGER
        );

        CREATE INDEX IF NOT EXISTS idx_signals_symbol ON signals(symbol);
        CREATE INDEX IF NOT EXISTS idx_signals_timestamp ON signals(timestamp);
        CREATE INDEX IF NOT EXISTS idx_signals_score ON signals(score DESC);
    """)
    conn.commit()


def save_signal(symbol: str, direction: str, score: int, price: float,
                tp1: float = 0, tp2: float = 0, tp3: float = 0, sl: float = 0,
                reasons: str = "", timeframe: str = "1h", confidence: int = 0,
                agent_reasoning: str = "") -> int:
    """Save a trading signal to the database"""
    conn = _get_connection()
    cursor = conn.execute(
        """INSERT INTO signals (symbol, direction, score, price, tp1, tp2, tp3, sl,
           reasons, timeframe, confidence, agent_reasoning)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (symbol, direction, score, price, tp1, tp2, tp3, sl,
         reasons, timeframe, confidence, agent_reasoning)
    )
    conn.commit()
    signal_id = cursor.lastrowid
    conn.close()
    return signal_id


def save_decision(query: str, response: str, tools_used: List[str],
                  model: str = "", duration_ms: int = 0) -> int:
    """Save an agent decision to the database"""
    conn = _get_connection()
    cursor = conn.execute(
        "INSERT INTO decisions (query, response, tools_used, model, duration_ms) VALUES (?, ?, ?, ?, ?)",
        (query, response, json.dumps(tools_used), model, duration_ms)
    )
    conn.commit()
    decision_id = cursor.lastrowid
    conn.close()
    return decision_id


def get_recent_signals(limit: int = 20, symbol: Optional[str] = None) -> List[Dict]:
    """Get recent signals, optionally filtered by symbol"""
    conn = _get_connection()
    if symbol:
        rows = conn.execute(
            "SELECT * FROM signals WHERE symbol = ? ORDER BY timestamp DESC LIMIT ?",
            (symbol, limit)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM signals ORDER BY timestamp DESC LIMIT ?", (limit,)
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_signal_stats() -> Dict:
    """Get aggregate statistics about signals"""
    conn = _get_connection()
    stats = {}
    stats['total'] = conn.execute("SELECT COUNT(*) FROM signals").fetchone()[0]
    stats['long'] = conn.execute("SELECT COUNT(*) FROM signals WHERE direction='LONG'").fetchone()[0]
    stats['short'] = conn.execute("SELECT COUNT(*) FROM signals WHERE direction='SHORT'").fetchone()[0]
    stats['avg_score'] = conn.execute("SELECT AVG(score) FROM signals").fetchone()[0] or 0
    stats['avg_confidence'] = conn.execute("SELECT AVG(confidence) FROM signals").fetchone()[0] or 0
    stats['top_symbols'] = [
        dict(r) for r in conn.execute(
            "SELECT symbol, COUNT(*) as count, AVG(score) as avg_score FROM signals GROUP BY symbol ORDER BY count DESC LIMIT 10"
        ).fetchall()
    ]
    conn.close()
    return stats
