"""
TradeOracle - MCP Server (FastMCP - Hardened)
Exposes Domino Pipeline + Price + History as MCP tools.
Features: Graceful degradation, never crashes on API errors.
"""
import json
import sys
import os
import time

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp.server.fastmcp import FastMCP

from pipeline.domino import run_domino
from tools.market_scanner import _fetch_mexc_tickers
from database.signals_db import get_pipeline_runs, get_last_pipeline_run, get_signal_stats
from config.settings import MEXC_TICKER_URL

import urllib.request

mcp = FastMCP("TradeOracle")


@mcp.tool()
def run_trading_pipeline(min_score: int = 70, top_n: int = 5, alert_threshold: int = 75) -> str:
    """Run the complete Domino trading pipeline: Scan 850+ MEXC Futures -> Filter -> Regime -> Analyze -> Score -> Signal -> Alert.
    Returns top trading opportunities with weighted scores, entry/TP/SL, and sends Telegram alerts for high-confidence signals.

    Args:
        min_score: Minimum scan score threshold (0-100). Default 70.
        top_n: Maximum symbols to deep-analyze. Default 5.
        alert_threshold: Minimum confidence to trigger Telegram alert. Default 75.
    """
    # Smart retry: if pipeline fails on transient error, retry once
    for attempt in range(2):
        result = run_domino(min_score=min_score, top_n=top_n, alert_threshold=alert_threshold)
        if result.get("status") != "FAILED" or attempt == 1:
            break
        err = result.get("error", "")
        if "429" in err or "503" in err or "timeout" in err.lower():
            time.sleep(3)
        else:
            break

    if result.get("error"):
        return f"Pipeline FAILED: {result['error']}"

    output = (
        f"DOMINO PIPELINE - Run #{result['run_id']}\n"
        f"{'='*50}\n"
        f"Status: {result['status']} in {result['duration_ms']}ms\n"
        f"Scanned: {result['scanned']} contracts | Filtered: {result['filtered']} | Analyzed: {result['analyzed']}\n"
        f"Regime: {result['regime']} (Bias: {result['regime_bias']})\n"
        f"Alerts sent: {result['alerts_sent']}\n\n"
    )

    if result['signals']:
        output += "SIGNALS:\n"
        for i, s in enumerate(result['signals'], 1):
            output += (
                f"\n{i}. {s['symbol']} | {s['direction']} | Score: {s['weighted_score']}/100 | Conf: {s['confidence']}%\n"
                f"   Entry: ${s['entry']:.6g} | TP1: ${s['tp1']:.6g} | TP2: ${s['tp2']:.6g} | TP3: ${s['tp3']:.6g} | SL: ${s['sl']:.6g}\n"
            )
    else:
        output += "No signals promoted (all below threshold).\n"

    return output


@mcp.tool()
def get_price(symbol: str) -> str:
    """Get current price and 24h stats for a cryptocurrency from MEXC Futures.

    Args:
        symbol: Trading pair (e.g. 'BTC/USDT', 'ETH/USDT', 'SOL/USDT').
    """
    mexc_symbol = symbol.replace('/', '_')
    try:
        url = f"{MEXC_TICKER_URL}?symbol={mexc_symbol}"
        with urllib.request.urlopen(url, timeout=10) as r:
            data = json.loads(r.read())

        t = data.get('data', {})
        if not t:
            return f"Symbol {symbol} not found on MEXC Futures."

        price = float(t.get('lastPrice') or 0)
        high24 = float(t.get('high24Price') or 0)
        low24 = float(t.get('low24Price') or 0)
        change = float(t.get('riseFallRate') or 0) * 100
        volume = float(t.get('amount24') or 0)
        funding = float(t.get('fundingRate') or 0) * 100

        range_24h = high24 - low24
        position = ((price - low24) / range_24h * 100) if range_24h > 0 else 50

        return (
            f"{symbol} - Current Market Data:\n"
            f"  Price: ${price:.6g}\n"
            f"  24h Change: {change:+.2f}%\n"
            f"  24h High: ${high24:.6g}\n"
            f"  24h Low: ${low24:.6g}\n"
            f"  Range Position: {position:.1f}%\n"
            f"  24h Volume: ${volume:,.0f}\n"
            f"  Funding Rate: {funding:.4f}%\n"
        )
    except Exception as e:
        return f"Error fetching {symbol}: {str(e)}"


@mcp.tool()
def get_pipeline_history(limit: int = 5) -> str:
    """Get recent Domino Pipeline run results from database.

    Args:
        limit: Number of recent runs to retrieve. Default 5.
    """
    runs = get_pipeline_runs(limit)
    if not runs:
        return "No pipeline runs found. Run the pipeline first with run_trading_pipeline."

    output = f"PIPELINE HISTORY (last {len(runs)} runs):\n{'='*50}\n"
    for run in runs:
        output += (
            f"\nRun #{run['id']} | {run['status']} | {run['started_at']}\n"
            f"  Scanned: {run['total_scanned']} | Signals: {run['signals_found']} | {run['duration_ms']}ms\n"
            f"  Regime: {run['regime']} ({run['regime_bias']})\n"
        )
        top = json.loads(run['top_symbols']) if run['top_symbols'] else []
        if top:
            output += f"  Top: {', '.join(top[:5])}\n"

        for a in run.get('analyses', [])[:3]:
            output += (
                f"    -> {a['symbol']} | {a['direction']} | Score: {a['weighted_score']:.0f} "
                f"| RSI: {a['rsi']:.1f} | {'PROMOTED' if a['promoted_to_signal'] else ''}\n"
            )
    return output


@mcp.resource("tradeoracle://status")
def get_status() -> str:
    """System status: DB stats + last pipeline run"""
    stats = get_signal_stats()
    last_run = get_last_pipeline_run()

    output = (
        f"TradeOracle Status\n"
        f"{'='*30}\n"
        f"Total signals: {stats['total']}\n"
        f"  LONG: {stats['long']} | SHORT: {stats['short']}\n"
        f"  Avg Score: {stats['avg_score']:.1f} | Avg Confidence: {stats['avg_confidence']:.1f}\n"
    )

    if last_run:
        output += (
            f"\nLast Pipeline Run: #{last_run['id']}\n"
            f"  Status: {last_run['status']} | {last_run['started_at']}\n"
            f"  Scanned: {last_run['total_scanned']} | Signals: {last_run['signals_found']}\n"
            f"  Regime: {last_run['regime']}\n"
        )

    return output
