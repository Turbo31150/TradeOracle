"""
TradeOracle - Technical Analysis Tools
Extracted from Symbiose Indicators v9.0 + Trading MCP Ultimate v3.7
RSI, MACD, ATR, Bollinger, Fibonacci, Pattern Detection
"""
import json
import urllib.request
import numpy as np
from typing import Dict, List, Tuple
from langchain_core.tools import tool

from config.settings import MEXC_KLINE_URL


def _fetch_ohlcv(symbol: str, interval: str = "Min60", limit: int = 100) -> List[List]:
    """Fetch OHLCV data from MEXC"""
    try:
        mexc_sym = symbol.replace('/', '_')
        url = f"{MEXC_KLINE_URL}/{mexc_sym}?interval={interval}&limit={limit}"
        with urllib.request.urlopen(url, timeout=15) as r:
            data = json.loads(r.read())
        kd = data.get('data', {})
        times = kd.get('time', [])
        opens = kd.get('open', [])
        highs = kd.get('high', [])
        lows = kd.get('low', [])
        closes = kd.get('close', [])
        vols = kd.get('vol', [])
        return [[times[i], float(opens[i]), float(highs[i]), float(lows[i]),
                 float(closes[i]), float(vols[i])] for i in range(len(times))]
    except:
        return []


# === INDICATOR CALCULATIONS ===

def _rsi(closes: np.ndarray, period: int = 14) -> np.ndarray:
    deltas = np.diff(closes)
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    avg_gain = np.zeros_like(closes)
    avg_loss = np.zeros_like(closes)
    avg_gain[period] = np.mean(gains[:period])
    avg_loss[period] = np.mean(losses[:period])
    for i in range(period + 1, len(closes)):
        avg_gain[i] = (avg_gain[i-1] * (period - 1) + gains[i-1]) / period
        avg_loss[i] = (avg_loss[i-1] * (period - 1) + losses[i-1]) / period
    rs = np.divide(avg_gain, avg_loss, where=avg_loss != 0, out=np.ones_like(avg_gain) * 100)
    return 100 - (100 / (1 + rs))


def _ema(data: np.ndarray, period: int) -> np.ndarray:
    ema = np.zeros_like(data)
    mult = 2 / (period + 1)
    ema[0] = data[0]
    for i in range(1, len(data)):
        ema[i] = (data[i] - ema[i-1]) * mult + ema[i-1]
    return ema


def _sma(data: np.ndarray, period: int) -> np.ndarray:
    return np.convolve(data, np.ones(period)/period, mode='same')


def _macd(closes: np.ndarray) -> Dict:
    ema12 = _ema(closes, 12)
    ema26 = _ema(closes, 26)
    macd_line = ema12 - ema26
    signal_line = _ema(macd_line, 9)
    histogram = macd_line - signal_line
    return {
        "macd": float(macd_line[-1]),
        "signal": float(signal_line[-1]),
        "histogram": float(histogram[-1]),
        "crossover": "BULLISH" if macd_line[-1] > signal_line[-1] and macd_line[-2] <= signal_line[-2]
                     else "BEARISH" if macd_line[-1] < signal_line[-1] and macd_line[-2] >= signal_line[-2]
                     else "NONE"
    }


def _atr(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, period: int = 14) -> np.ndarray:
    tr = np.zeros_like(closes)
    tr[0] = highs[0] - lows[0]
    for i in range(1, len(closes)):
        tr[i] = max(highs[i] - lows[i], abs(highs[i] - closes[i-1]), abs(lows[i] - closes[i-1]))
    return _sma(tr, period)


def _bollinger(closes: np.ndarray, period: int = 20, std_dev: float = 2.0):
    middle = _sma(closes, period)
    std = np.zeros_like(closes)
    for i in range(period, len(closes)):
        std[i] = np.std(closes[i-period:i])
    return middle, middle + std * std_dev, middle - std * std_dev


def _stochastic(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, k_period: int = 14) -> Dict:
    k_values = np.zeros_like(closes)
    for i in range(k_period, len(closes)):
        h = np.max(highs[i-k_period:i+1])
        l = np.min(lows[i-k_period:i+1])
        if h != l:
            k_values[i] = ((closes[i] - l) / (h - l)) * 100
    d_values = _sma(k_values, 3)
    return {"k": float(k_values[-1]), "d": float(d_values[-1])}


def _obv(closes: np.ndarray, volumes: np.ndarray) -> float:
    obv = np.zeros_like(closes)
    for i in range(1, len(closes)):
        if closes[i] > closes[i-1]:
            obv[i] = obv[i-1] + volumes[i]
        elif closes[i] < closes[i-1]:
            obv[i] = obv[i-1] - volumes[i]
        else:
            obv[i] = obv[i-1]
    obv_ma = _sma(obv, 20)
    return "ACCUMULATION" if obv[-1] > obv_ma[-1] else "DISTRIBUTION"


def _detect_patterns(opens, highs, lows, closes) -> List[str]:
    """Detect candlestick patterns"""
    patterns = []
    if len(closes) < 3:
        return patterns

    body = abs(closes[-1] - opens[-1])
    range_size = highs[-1] - lows[-1]
    if range_size > 0 and body / range_size < 0.1:
        patterns.append("Doji (reversal)")

    upper_wick = highs[-1] - max(opens[-1], closes[-1])
    lower_wick = min(opens[-1], closes[-1]) - lows[-1]
    if lower_wick > body * 2 and upper_wick < body * 0.5:
        patterns.append("Hammer (bullish reversal)" if closes[-2] > closes[-1] else "Hanging Man (bearish)")

    if len(closes) >= 2:
        prev_body = abs(closes[-2] - opens[-2])
        curr_body = abs(closes[-1] - opens[-1])
        if curr_body > prev_body * 1.5:
            if closes[-1] > opens[-1] and closes[-2] < opens[-2]:
                patterns.append("Bullish Engulfing")
            elif closes[-1] < opens[-1] and closes[-2] > opens[-2]:
                patterns.append("Bearish Engulfing")

    return patterns


def _fibonacci_levels(highs, lows, closes) -> Dict:
    """Calculate Fibonacci retracement levels"""
    lookback = min(50, len(closes))
    swing_high = np.max(highs[-lookback:])
    swing_low = np.min(lows[-lookback:])
    diff = swing_high - swing_low
    current = closes[-1]

    levels = {
        "0.0%": float(swing_low),
        "23.6%": float(swing_low + diff * 0.236),
        "38.2%": float(swing_low + diff * 0.382),
        "50.0%": float(swing_low + diff * 0.5),
        "61.8%": float(swing_low + diff * 0.618),
        "78.6%": float(swing_low + diff * 0.786),
        "100%": float(swing_high),
    }

    nearest_support = None
    nearest_resistance = None
    for name, price in levels.items():
        if price < current and (nearest_support is None or price > nearest_support[1]):
            nearest_support = (name, price)
        elif price > current and (nearest_resistance is None or price < nearest_resistance[1]):
            nearest_resistance = (name, price)

    return {
        "levels": levels,
        "nearest_support": f"{nearest_support[0]} at ${nearest_support[1]:.6g}" if nearest_support else "None",
        "nearest_resistance": f"{nearest_resistance[0]} at ${nearest_resistance[1]:.6g}" if nearest_resistance else "None",
    }


def _full_analysis(ohlcv: List[List]) -> Dict:
    """Run full technical analysis on OHLCV data"""
    if len(ohlcv) < 50:
        return {"error": "Need at least 50 candles for analysis"}

    opens = np.array([c[1] for c in ohlcv])
    highs = np.array([c[2] for c in ohlcv])
    lows = np.array([c[3] for c in ohlcv])
    closes = np.array([c[4] for c in ohlcv])
    volumes = np.array([c[5] for c in ohlcv])

    rsi_val = _rsi(closes, 14)[-1]
    macd_data = _macd(closes)
    atr_val = _atr(highs, lows, closes, 14)[-1]
    atr_pct = (atr_val / closes[-1]) * 100
    bb_mid, bb_up, bb_low = _bollinger(closes, 20, 2)
    stoch = _stochastic(highs, lows, closes)
    obv_trend = _obv(closes, volumes)
    patterns = _detect_patterns(opens, highs, lows, closes)
    fib = _fibonacci_levels(highs, lows, closes)

    # EMA alignment
    ema5 = _ema(closes, 5)[-1]
    ema10 = _ema(closes, 10)[-1]
    ema20 = _ema(closes, 20)[-1]
    if ema5 > ema10 > ema20:
        ema_status = "BULLISH_ALIGNED"
    elif ema5 < ema10 < ema20:
        ema_status = "BEARISH_ALIGNED"
    else:
        ema_status = "MIXED"

    # BB squeeze detection
    bb_width = (bb_up[-1] - bb_low[-1]) / bb_mid[-1] * 100
    bb_width_avg = np.mean([(bb_up[i] - bb_low[i]) / bb_mid[i] * 100 for i in range(-20, 0)])
    in_squeeze = bb_width < bb_width_avg * 0.8

    # Composite score (0-100)
    score = 50
    if rsi_val < 30: score += 15  # Oversold
    elif rsi_val > 70: score -= 10  # Overbought
    if macd_data["crossover"] == "BULLISH": score += 10
    elif macd_data["crossover"] == "BEARISH": score -= 10
    if macd_data["histogram"] > 0: score += 5
    else: score -= 5
    if ema_status == "BULLISH_ALIGNED": score += 10
    elif ema_status == "BEARISH_ALIGNED": score -= 10
    if obv_trend == "ACCUMULATION": score += 5
    else: score -= 5
    if in_squeeze: score += 5
    score = max(0, min(100, score))

    # Direction
    if score >= 65:
        direction = "LONG"
    elif score <= 35:
        direction = "SHORT"
    else:
        direction = "NEUTRAL"

    # Entry/TP/SL
    entry = closes[-1]
    if direction == "LONG":
        tp1 = entry * 1.015
        tp2 = entry * 1.030
        tp3 = entry * 1.055
        sl = entry * 0.988
    elif direction == "SHORT":
        tp1 = entry * 0.985
        tp2 = entry * 0.970
        tp3 = entry * 0.945
        sl = entry * 1.012
    else:
        tp1 = tp2 = tp3 = sl = entry

    return {
        "price": float(closes[-1]),
        "rsi": float(rsi_val),
        "macd": macd_data,
        "atr": float(atr_val),
        "atr_pct": float(atr_pct),
        "stochastic": stoch,
        "obv_trend": obv_trend,
        "ema_status": ema_status,
        "ema": {"ema5": float(ema5), "ema10": float(ema10), "ema20": float(ema20)},
        "bollinger": {
            "upper": float(bb_up[-1]),
            "middle": float(bb_mid[-1]),
            "lower": float(bb_low[-1]),
            "width": float(bb_width),
            "in_squeeze": in_squeeze
        },
        "fibonacci": fib,
        "patterns": patterns,
        "composite_score": score,
        "direction": direction,
        "entry": float(entry),
        "tp1": float(tp1),
        "tp2": float(tp2),
        "tp3": float(tp3),
        "sl": float(sl),
    }


@tool
def analyze_coin_technical(symbol: str, timeframe: str = "1h") -> str:
    """Perform deep technical analysis on a cryptocurrency including RSI, MACD, ATR,
    Bollinger Bands, Stochastic, OBV, EMA alignment, candlestick patterns,
    Fibonacci levels, and a composite trading score with entry/TP/SL.

    Args:
        symbol: Trading pair (e.g. 'BTC/USDT', 'ETH/USDT').
        timeframe: Analysis timeframe - '15m', '1h', '4h', '1d'. Default '1h'.
    """
    tf_map = {"15m": "Min15", "30m": "Min30", "1h": "Min60", "4h": "Hour4", "1d": "Day1"}
    interval = tf_map.get(timeframe, "Min60")

    ohlcv = _fetch_ohlcv(symbol, interval, 100)
    if not ohlcv or len(ohlcv) < 50:
        return f"Error: Not enough data for {symbol}. Need 50+ candles, got {len(ohlcv)}."

    a = _full_analysis(ohlcv)
    if "error" in a:
        return f"Analysis error: {a['error']}"

    result = f"TECHNICAL ANALYSIS: {symbol} ({timeframe})\n"
    result += f"{'='*50}\n\n"
    result += f"PRICE: ${a['price']:.6g}\n\n"

    result += "INDICATORS:\n"
    result += f"  RSI(14): {a['rsi']:.1f} {'(OVERSOLD)' if a['rsi'] < 30 else '(OVERBOUGHT)' if a['rsi'] > 70 else ''}\n"
    result += f"  MACD: {a['macd']['macd']:.6g} | Signal: {a['macd']['signal']:.6g} | Hist: {a['macd']['histogram']:.6g}\n"
    result += f"  MACD Crossover: {a['macd']['crossover']}\n"
    result += f"  Stochastic: %K={a['stochastic']['k']:.1f} %D={a['stochastic']['d']:.1f}\n"
    result += f"  ATR(14): {a['atr']:.6g} ({a['atr_pct']:.2f}%)\n"
    result += f"  OBV Trend: {a['obv_trend']}\n"
    result += f"  EMA Alignment: {a['ema_status']} (5={a['ema']['ema5']:.6g} 10={a['ema']['ema10']:.6g} 20={a['ema']['ema20']:.6g})\n\n"

    result += "BOLLINGER BANDS:\n"
    bb = a['bollinger']
    result += f"  Upper: ${bb['upper']:.6g} | Middle: ${bb['middle']:.6g} | Lower: ${bb['lower']:.6g}\n"
    result += f"  Width: {bb['width']:.2f}% | Squeeze: {'YES' if bb['in_squeeze'] else 'No'}\n\n"

    result += "FIBONACCI LEVELS:\n"
    result += f"  Support: {a['fibonacci']['nearest_support']}\n"
    result += f"  Resistance: {a['fibonacci']['nearest_resistance']}\n\n"

    if a['patterns']:
        result += f"PATTERNS DETECTED: {', '.join(a['patterns'])}\n\n"

    result += f"COMPOSITE SCORE: {a['composite_score']}/100\n"
    result += f"DIRECTION: {a['direction']}\n\n"

    if a['direction'] != "NEUTRAL":
        result += "TRADE SETUP:\n"
        result += f"  Entry: ${a['entry']:.6g}\n"
        result += f"  TP1: ${a['tp1']:.6g} (+1.5%)\n"
        result += f"  TP2: ${a['tp2']:.6g} (+3.0%)\n"
        result += f"  TP3: ${a['tp3']:.6g} (+5.5%)\n"
        result += f"  SL: ${a['sl']:.6g} (-1.2%)\n"

    return result


@tool
def get_market_regime(symbol: str = "BTC/USDT") -> str:
    """Determine the current market regime (trending up/down, ranging, volatile, breakout)
    using ADX, ATR, and directional indicators.

    Args:
        symbol: Reference symbol for regime detection. Default 'BTC/USDT'.
    """
    ohlcv = _fetch_ohlcv(symbol, "Hour4", 100)
    if not ohlcv or len(ohlcv) < 50:
        return f"Cannot determine regime: insufficient data for {symbol}."

    highs = np.array([c[2] for c in ohlcv])
    lows = np.array([c[3] for c in ohlcv])
    closes = np.array([c[4] for c in ohlcv])

    atr_val = _atr(highs, lows, closes, 14)
    atr_pct = (atr_val[-1] / closes[-1]) * 100

    # ADX calculation
    plus_dm = np.zeros_like(highs)
    minus_dm = np.zeros_like(highs)
    for i in range(1, len(highs)):
        up = highs[i] - highs[i-1]
        down = lows[i-1] - lows[i]
        if up > down and up > 0: plus_dm[i] = up
        if down > up and down > 0: minus_dm[i] = down
    plus_di = 100 * _ema(plus_dm, 14) / (atr_val + 0.0001)
    minus_di = 100 * _ema(minus_dm, 14) / (atr_val + 0.0001)
    dx = np.abs(plus_di - minus_di) / (plus_di + minus_di + 0.0001) * 100
    adx = float(np.mean(dx[-14:]))

    # Regime detection
    if adx > 25:
        if plus_di[-1] > minus_di[-1]:
            regime = "TRENDING UP"
            bias = "LONG"
        else:
            regime = "TRENDING DOWN"
            bias = "SHORT"
    elif atr_pct > 3:
        regime = "VOLATILE"
        bias = "REDUCE SIZE"
    else:
        regime = "RANGING"
        bias = "MEAN REVERSION"

    high_20 = np.max(highs[-20:])
    if closes[-1] >= high_20 * 0.99:
        regime = "BREAKOUT"
        bias = "LONG"

    change_1h = (closes[-1] - closes[-2]) / closes[-2] * 100 if len(closes) > 1 else 0
    rsi_val = _rsi(closes, 14)[-1]

    return (
        f"MARKET REGIME: {regime}\n"
        f"Reference: {symbol} (4H)\n\n"
        f"ADX: {adx:.1f} {'(Strong Trend)' if adx > 25 else '(Weak/No Trend)'}\n"
        f"+DI: {plus_di[-1]:.1f} | -DI: {minus_di[-1]:.1f}\n"
        f"ATR%: {atr_pct:.2f}%\n"
        f"RSI: {rsi_val:.1f}\n"
        f"Price: ${closes[-1]:.6g} ({change_1h:+.2f}% last candle)\n\n"
        f"Trading Bias: {bias}\n"
        f"Recommendation: {'Trend-following strategies' if 'TRENDING' in regime else 'Range-bound strategies' if regime == 'RANGING' else 'Breakout strategies' if regime == 'BREAKOUT' else 'Reduce exposure, high volatility'}"
    )


@tool
def multi_timeframe_analysis(symbol: str) -> str:
    """Perform multi-timeframe analysis on a cryptocurrency (15m + 1h + 4h).
    Shows trend alignment across timeframes for higher-confidence signals.

    Args:
        symbol: Trading pair (e.g. 'BTC/USDT').
    """
    results = []
    for tf_label, tf_api in [("15m", "Min15"), ("1h", "Min60"), ("4h", "Hour4")]:
        ohlcv = _fetch_ohlcv(symbol, tf_api, 100)
        if not ohlcv or len(ohlcv) < 50:
            results.append({"tf": tf_label, "error": "Insufficient data"})
            continue
        a = _full_analysis(ohlcv)
        results.append({
            "tf": tf_label,
            "direction": a.get("direction", "N/A"),
            "score": a.get("composite_score", 0),
            "rsi": a.get("rsi", 0),
            "macd_cross": a.get("macd", {}).get("crossover", "NONE"),
            "ema": a.get("ema_status", "N/A"),
            "squeeze": a.get("bollinger", {}).get("in_squeeze", False),
        })

    output = f"MULTI-TIMEFRAME ANALYSIS: {symbol}\n{'='*50}\n\n"
    directions = []
    for r in results:
        if "error" in r:
            output += f"[{r['tf']}] Error: {r['error']}\n"
            continue
        output += (f"[{r['tf']}] Score: {r['score']}/100 | Direction: {r['direction']} | "
                   f"RSI: {r['rsi']:.1f} | MACD: {r['macd_cross']} | EMA: {r['ema']}"
                   f"{' | SQUEEZE' if r['squeeze'] else ''}\n")
        directions.append(r['direction'])

    # Alignment check
    output += "\n"
    if len(set(directions)) == 1 and directions[0] != "NEUTRAL":
        output += f"ALIGNMENT: ALL TIMEFRAMES AGREE -> {directions[0]} (High Confidence)\n"
    elif len(set(d for d in directions if d != "NEUTRAL")) == 1:
        d = [d for d in directions if d != "NEUTRAL"][0]
        output += f"ALIGNMENT: PARTIAL -> {d} (Some timeframes neutral)\n"
    else:
        output += "ALIGNMENT: CONFLICTING signals across timeframes (Low Confidence)\n"

    return output
