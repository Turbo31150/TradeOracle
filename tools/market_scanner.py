"""
TradeOracle - Market Scanner Tools
Extracted from Trading AI Ultimate MCP v3.7
Scans 850+ MEXC Futures contracts with composite scoring
"""
import json
import math
import urllib.request
from typing import Dict, List, Optional
from langchain_core.tools import tool

from config.settings import MEXC_TICKER_URL, MEXC_KLINE_URL, SCANNER_CONFIG


def _fetch_mexc_tickers() -> List[Dict]:
    """Fetch all MEXC Futures tickers"""
    try:
        with urllib.request.urlopen(MEXC_TICKER_URL, timeout=15) as r:
            data = json.loads(r.read())
        return data.get('data', [])
    except Exception as e:
        return []


def _fetch_klines(symbol: str, interval: str = "Min60", limit: int = 100) -> Dict:
    """Fetch OHLCV klines from MEXC Futures API"""
    try:
        url = f"{MEXC_KLINE_URL}/{symbol}?interval={interval}&limit={limit}"
        with urllib.request.urlopen(url, timeout=15) as r:
            data = json.loads(r.read())

        kline_data = data.get('data', {})
        times = kline_data.get('time', [])
        opens = kline_data.get('open', [])
        highs = kline_data.get('high', [])
        lows = kline_data.get('low', [])
        closes = kline_data.get('close', [])
        vols = kline_data.get('vol', [])

        ohlcv = []
        for i in range(len(times)):
            ohlcv.append([
                times[i],
                float(opens[i]),
                float(highs[i]),
                float(lows[i]),
                float(closes[i]),
                float(vols[i])
            ])
        return {"success": True, "ohlcv": ohlcv, "symbol": symbol}
    except Exception as e:
        return {"success": False, "error": str(e)}


@tool
def scan_market(min_score: int = 70) -> str:
    """Scan 850+ MEXC Futures contracts and return top trading opportunities with scores.
    Each signal includes: symbol, price, 24h change, composite score (0-100),
    signal type (PRIME/STRONG/STANDARD), direction (LONG/SHORT), and reasons.

    Args:
        min_score: Minimum score threshold (0-100). Default 70.
    """
    min_volume = SCANNER_CONFIG["min_volume_24h"]
    max_signals = SCANNER_CONFIG["max_signals"]

    tickers = _fetch_mexc_tickers()
    if not tickers:
        return "Error: Could not fetch MEXC market data. API may be down."

    signals = []
    for t in tickers:
        if not t.get('symbol', '').endswith('_USDT'):
            continue

        symbol = t['symbol'].replace('_USDT', '/USDT')
        price = float(t.get('lastPrice') or 0)

        high24_raw = t.get('high24Price')
        low24_raw = t.get('low24Price')
        high24 = float(high24_raw) if high24_raw is not None else price * 1.05
        low24 = float(low24_raw) if low24_raw is not None else price * 0.95

        change_raw = t.get('riseFallRate')
        change = float(change_raw) * 100 if change_raw is not None else 0
        volume = float(t.get('amount24') or 0)
        funding_rate = float(t.get('fundingRate') or 0)

        if price <= 0 or volume < min_volume:
            continue

        # Position in 24h range (0=low, 1=high)
        range_24h = high24 - low24
        if range_24h > 0 and range_24h / price < 0.5:
            position = (price - low24) / range_24h
        else:
            position = 0.5 + (change / 100) if abs(change) < 50 else 0.5
        position = max(0.0, min(1.0, position))

        volatility = (range_24h / price * 100) if price > 0 else 0

        # === COMPOSITE SCORING (0-100) ===
        score = 30
        reasons = []

        # Volume scoring (log scale, max 25pts)
        if volume > 0:
            vol_log = math.log10(volume)
            if vol_log >= 10:
                score += 25; reasons.append('WHALE_VOLUME')
            elif vol_log >= 9:
                score += 20; reasons.append('MEGA_VOLUME')
            elif vol_log >= 8:
                score += 15; reasons.append('HIGH_VOLUME')
            elif vol_log >= 7:
                score += 10; reasons.append('MED_VOLUME')
            elif vol_log >= 6:
                score += 5; reasons.append('OK_VOLUME')

        # Position scoring (max 25pts)
        if position >= 0.95:
            score += 25; reasons.append('BREAKOUT_ZONE')
        elif position >= 0.85:
            score += 20; reasons.append('HIGH_RANGE')
        elif position >= 0.70:
            score += 10; reasons.append('UPPER_MID')
        elif position <= 0.05:
            score += 22; reasons.append('REVERSAL_ZONE')
        elif position <= 0.15:
            score += 18; reasons.append('LOW_RANGE')
        elif position <= 0.30:
            score += 8; reasons.append('LOWER_MID')

        # Momentum scoring (max 20pts)
        abs_change = abs(change)
        if abs_change >= 20:
            score += 20; reasons.append('PUMP' if change > 0 else 'DUMP')
        elif abs_change >= 10:
            score += 15; reasons.append('STRONG_MOVE')
        elif abs_change >= 5:
            score += 10; reasons.append('MOMENTUM')
        elif abs_change >= 2:
            score += 5; reasons.append('TREND')

        # Volatility bonus (max 10pts)
        if volatility >= 15:
            score += 10; reasons.append('HIGH_VOLATILITY')
        elif volatility >= 8:
            score += 5; reasons.append('MED_VOLATILITY')

        # Confluence bonus
        if position >= 0.90 and change > 0 and volume > 50_000_000:
            score += 10; reasons.append('BREAKOUT_CONFIRMED')
        elif position <= 0.10 and volume > 50_000_000:
            score += 8; reasons.append('CAPITULATION')

        # Direction
        if position >= 0.70 and change > 0:
            direction = 'LONG'
        elif position <= 0.30 and change < 0:
            direction = 'SHORT'
        elif change > 2:
            direction = 'LONG'
        elif change < -2:
            direction = 'SHORT'
        else:
            direction = 'NEUTRAL'

        # Signal type
        if score >= 90:
            signal_type = 'PRIME'
        elif score >= 80:
            signal_type = 'STRONG'
        elif score >= 70:
            signal_type = 'STANDARD'
        else:
            signal_type = 'WEAK'

        if score >= min_score:
            signals.append({
                'symbol': symbol,
                'price': price,
                'change_24h': round(change, 2),
                'score': min(100, score),
                'signal_type': signal_type,
                'range_position': round(position * 100, 1),
                'volatility': round(volatility, 2),
                'volume_24h': volume,
                'funding_rate': round(funding_rate * 100, 4),
                'direction': direction,
                'reasons': reasons[:5]
            })

    signals.sort(key=lambda x: (x['score'], x['volume_24h']), reverse=True)
    top = signals[:max_signals]

    if not top:
        return f"No signals found with score >= {min_score}. Market may be quiet. Try lowering min_score."

    result = f"MEXC Futures Scan: {len(tickers)} contracts analyzed, {len(signals)} signals found (score >= {min_score})\n\n"
    result += "TOP OPPORTUNITIES:\n"
    for i, s in enumerate(top, 1):
        result += (
            f"\n{i}. {s['symbol']} | Score: {s['score']}/100 ({s['signal_type']})\n"
            f"   Price: ${s['price']:.6g} | Change 24h: {s['change_24h']:+.2f}%\n"
            f"   Direction: {s['direction']} | Range Position: {s['range_position']}%\n"
            f"   Volume 24h: ${s['volume_24h']:,.0f} | Funding: {s['funding_rate']}%\n"
            f"   Reasons: {', '.join(s['reasons'])}\n"
        )
    return result


@tool
def get_coin_price(symbol: str) -> str:
    """Get the current price and 24h stats for a specific cryptocurrency from MEXC Futures.

    Args:
        symbol: The trading pair symbol (e.g. 'BTC/USDT', 'ETH/USDT', 'SOL/USDT').
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
            f"  Range Position: {position:.1f}% (0%=low, 100%=high)\n"
            f"  24h Volume: ${volume:,.0f}\n"
            f"  Funding Rate: {funding:.4f}%\n"
        )
    except Exception as e:
        return f"Error fetching {symbol}: {str(e)}"


@tool
def get_top_movers(direction: str = "gainers", limit: int = 10) -> str:
    """Get top gaining or losing cryptocurrencies on MEXC Futures in the last 24h.

    Args:
        direction: 'gainers' for top pumps or 'losers' for top dumps. Default 'gainers'.
        limit: Number of results to return. Default 10.
    """
    tickers = _fetch_mexc_tickers()
    if not tickers:
        return "Error: Could not fetch MEXC data."

    coins = []
    for t in tickers:
        if not t.get('symbol', '').endswith('_USDT'):
            continue
        change_raw = t.get('riseFallRate')
        if change_raw is None:
            continue
        change = float(change_raw) * 100
        volume = float(t.get('amount24') or 0)
        if volume < 100000:
            continue
        coins.append({
            'symbol': t['symbol'].replace('_USDT', '/USDT'),
            'price': float(t.get('lastPrice') or 0),
            'change': round(change, 2),
            'volume': volume,
        })

    if direction == "losers":
        coins.sort(key=lambda x: x['change'])
    else:
        coins.sort(key=lambda x: x['change'], reverse=True)

    top = coins[:limit]
    title = "TOP GAINERS" if direction == "gainers" else "TOP LOSERS"
    result = f"{title} (24h) - MEXC Futures:\n\n"
    for i, c in enumerate(top, 1):
        result += f"{i}. {c['symbol']} | {c['change']:+.2f}% | ${c['price']:.6g} | Vol: ${c['volume']:,.0f}\n"
    return result


@tool
def get_ohlcv_data(symbol: str, timeframe: str = "1h", limit: int = 100) -> str:
    """Get OHLCV (Open/High/Low/Close/Volume) candlestick data for technical analysis.

    Args:
        symbol: Trading pair (e.g. 'BTC/USDT').
        timeframe: Candle timeframe - '15m', '1h', '4h', or '1d'. Default '1h'.
        limit: Number of candles. Default 100.
    """
    tf_map = {"1m": "Min1", "5m": "Min5", "15m": "Min15", "30m": "Min30",
              "1h": "Min60", "4h": "Hour4", "8h": "Hour8", "1d": "Day1"}
    interval = tf_map.get(timeframe, "Min60")
    mexc_symbol = symbol.replace('/', '_')

    result = _fetch_klines(mexc_symbol, interval, limit)
    if not result["success"]:
        return f"Error fetching klines for {symbol}: {result.get('error')}"

    ohlcv = result["ohlcv"]
    if not ohlcv:
        return f"No kline data returned for {symbol}."

    last = ohlcv[-1]
    prev = ohlcv[-2] if len(ohlcv) > 1 else last

    summary = f"{symbol} OHLCV ({timeframe}, last {len(ohlcv)} candles):\n"
    summary += f"  Latest Candle: O={last[1]:.6g} H={last[2]:.6g} L={last[3]:.6g} C={last[4]:.6g} V={last[5]:.0f}\n"
    summary += f"  Previous: O={prev[1]:.6g} H={prev[2]:.6g} L={prev[3]:.6g} C={prev[4]:.6g}\n"

    # Basic stats
    closes = [c[4] for c in ohlcv]
    highs = [c[2] for c in ohlcv]
    lows = [c[3] for c in ohlcv]
    vols = [c[5] for c in ohlcv]

    summary += f"  Period High: ${max(highs):.6g}\n"
    summary += f"  Period Low: ${min(lows):.6g}\n"
    summary += f"  Avg Volume: {sum(vols)/len(vols):,.0f}\n"
    summary += f"  Latest Volume vs Avg: {vols[-1]/(sum(vols)/len(vols))*100:.0f}%\n"

    return summary
