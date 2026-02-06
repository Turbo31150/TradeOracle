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

        -- Pipeline tables
        CREATE TABLE IF NOT EXISTS pipeline_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            started_at TEXT DEFAULT (datetime('now')),
            completed_at TEXT,
            status TEXT DEFAULT 'RUNNING',
            total_scanned INTEGER DEFAULT 0,
            signals_found INTEGER DEFAULT 0,
            top_symbols TEXT,
            regime TEXT,
            regime_bias TEXT,
            duration_ms INTEGER
        );

        CREATE TABLE IF NOT EXISTS pipeline_analyses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id INTEGER REFERENCES pipeline_runs(id),
            symbol TEXT NOT NULL,
            timeframe TEXT DEFAULT '1h',
            price REAL,
            rsi REAL,
            macd_histogram REAL,
            ema_status TEXT,
            obv_trend TEXT,
            bb_squeeze INTEGER DEFAULT 0,
            stoch_k REAL,
            patterns TEXT,
            scan_score INTEGER,
            technical_score INTEGER,
            regime_adjustment REAL,
            weighted_score REAL,
            direction TEXT,
            entry_price REAL,
            tp1 REAL, tp2 REAL, tp3 REAL,
            sl REAL,
            confidence INTEGER,
            promoted_to_signal INTEGER DEFAULT 0
        );

        CREATE INDEX IF NOT EXISTS idx_pa_run ON pipeline_analyses(run_id);
        CREATE INDEX IF NOT EXISTS idx_pa_symbol ON pipeline_analyses(symbol);

        CREATE TABLE IF NOT EXISTS ai_votes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id INTEGER REFERENCES pipeline_runs(id),
            symbol TEXT NOT NULL,
            model_name TEXT,
            model_id TEXT,
            direction TEXT,
            confidence INTEGER,
            reason TEXT,
            elapsed_ms INTEGER,
            status TEXT,
            timestamp TEXT DEFAULT (datetime('now'))
        );

        CREATE INDEX IF NOT EXISTS idx_av_run ON ai_votes(run_id);
        CREATE INDEX IF NOT EXISTS idx_av_symbol ON ai_votes(symbol);
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


def create_pipeline_run() -> int:
    """Create a new pipeline run entry, return run_id"""
    conn = _get_connection()
    cursor = conn.execute("INSERT INTO pipeline_runs DEFAULT VALUES")
    conn.commit()
    run_id = cursor.lastrowid
    conn.close()
    return run_id


def save_pipeline_analysis(run_id: int, data: Dict) -> int:
    """Save a pipeline analysis for a symbol"""
    conn = _get_connection()
    cursor = conn.execute(
        """INSERT INTO pipeline_analyses
           (run_id, symbol, timeframe, price, rsi, macd_histogram, ema_status,
            obv_trend, bb_squeeze, stoch_k, patterns, scan_score, technical_score,
            regime_adjustment, weighted_score, direction, entry_price,
            tp1, tp2, tp3, sl, confidence, promoted_to_signal)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (run_id, data.get('symbol'), data.get('timeframe', '1h'),
         data.get('price'), data.get('rsi'), data.get('macd_histogram'),
         data.get('ema_status'), data.get('obv_trend'),
         1 if data.get('bb_squeeze') else 0, data.get('stoch_k'),
         json.dumps(data.get('patterns', [])),
         data.get('scan_score'), data.get('technical_score'),
         data.get('regime_adjustment', 0), data.get('weighted_score'),
         data.get('direction'), data.get('entry_price'),
         data.get('tp1'), data.get('tp2'), data.get('tp3'), data.get('sl'),
         data.get('confidence', 0), data.get('promoted_to_signal', 0))
    )
    conn.commit()
    analysis_id = cursor.lastrowid
    conn.close()
    return analysis_id


def complete_pipeline_run(run_id: int, status: str = "COMPLETED",
                          duration_ms: int = 0, total_scanned: int = 0,
                          signals_found: int = 0, top_symbols: List = None,
                          regime: str = "", regime_bias: str = ""):
    """Finalize a pipeline run with results"""
    conn = _get_connection()
    conn.execute(
        """UPDATE pipeline_runs SET
           completed_at = datetime('now'), status = ?, duration_ms = ?,
           total_scanned = ?, signals_found = ?,
           top_symbols = ?, regime = ?, regime_bias = ?
           WHERE id = ?""",
        (status, duration_ms, total_scanned, signals_found,
         json.dumps(top_symbols or []), regime, regime_bias, run_id)
    )
    conn.commit()
    conn.close()


def get_last_pipeline_run() -> Optional[Dict]:
    """Get the most recent pipeline run with its analyses"""
    conn = _get_connection()
    run = conn.execute(
        "SELECT * FROM pipeline_runs ORDER BY id DESC LIMIT 1"
    ).fetchone()
    if not run:
        conn.close()
        return None
    run_dict = dict(run)
    analyses = conn.execute(
        "SELECT * FROM pipeline_analyses WHERE run_id = ? ORDER BY weighted_score DESC",
        (run_dict['id'],)
    ).fetchall()
    run_dict['analyses'] = [dict(a) for a in analyses]
    conn.close()
    return run_dict


def get_pipeline_runs(limit: int = 5) -> List[Dict]:
    """Get recent pipeline runs with summary"""
    conn = _get_connection()
    runs = conn.execute(
        "SELECT * FROM pipeline_runs ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
    result = []
    for run in runs:
        rd = dict(run)
        rd['analyses'] = [dict(a) for a in conn.execute(
            "SELECT * FROM pipeline_analyses WHERE run_id = ? ORDER BY weighted_score DESC",
            (rd['id'],)
        ).fetchall()]
        result.append(rd)
    conn.close()
    return result


def save_ai_votes(run_id: int, symbol: str, votes: List[Dict]):
    """Save AI consensus votes to database"""
    conn = _get_connection()
    for v in votes:
        conn.execute(
            """INSERT INTO ai_votes (run_id, symbol, model_name, model_id,
               direction, confidence, reason, elapsed_ms, status)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (run_id, symbol, v.get('name'), v.get('model'),
             v.get('direction'), v.get('confidence'),
             v.get('reason', '')[:500], v.get('elapsed_ms', 0),
             v.get('status', 'UNKNOWN'))
        )
    conn.commit()
    conn.close()


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
