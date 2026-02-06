"""
TradeOracle - Domino Pipeline
1 command = Scan -> Filter -> Regime -> Analyze -> Score -> Signal -> Alert
Progressive scoring and SQLite persistence at each step.
"""
import json
import time
import math
import urllib.request
import urllib.parse
import numpy as np
from typing import Dict, List, Optional

from config.settings import (
    MEXC_TICKER_URL, MEXC_KLINE_URL, SCANNER_CONFIG,
    TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, TRADING_CONFIG
)
from database.signals_db import (
    create_pipeline_run, save_pipeline_analysis, complete_pipeline_run,
    save_signal, save_ai_votes
)
from pipeline.ai_consensus import run_ai_consensus
from tools.market_scanner import _fetch_mexc_tickers, _fetch_klines
from tools.technical_analysis import (
    _fetch_ohlcv, _full_analysis, _rsi, _ema, _atr
)

# === WEIGHTS ===
WEIGHTS = {
    "scan_score": 0.20,
    "technical_score": 0.30,
    "regime_bonus": 0.10,
    "mtf_alignment": 0.10,
    "ai_consensus": 0.30,   # 4 AI models vote
}


def _detect_regime(btc_ohlcv: List[List]) -> Dict:
    """Detect market regime from BTC 4H data"""
    if not btc_ohlcv or len(btc_ohlcv) < 50:
        return {"regime": "UNKNOWN", "bias": "NEUTRAL", "adjustment": 0}

    highs = np.array([c[2] for c in btc_ohlcv])
    lows = np.array([c[3] for c in btc_ohlcv])
    closes = np.array([c[4] for c in btc_ohlcv])

    atr_val = _atr(highs, lows, closes, 14)
    atr_pct = (atr_val[-1] / closes[-1]) * 100

    # ADX
    plus_dm = np.zeros_like(highs)
    minus_dm = np.zeros_like(highs)
    for i in range(1, len(highs)):
        up = highs[i] - highs[i-1]
        down = lows[i-1] - lows[i]
        if up > down and up > 0:
            plus_dm[i] = up
        if down > up and down > 0:
            minus_dm[i] = down
    plus_di = 100 * _ema(plus_dm, 14) / (atr_val + 0.0001)
    minus_di = 100 * _ema(minus_dm, 14) / (atr_val + 0.0001)
    dx = np.abs(plus_di - minus_di) / (plus_di + minus_di + 0.0001) * 100
    adx = float(np.mean(dx[-14:]))

    if adx > 25:
        if plus_di[-1] > minus_di[-1]:
            regime, bias = "TRENDING_UP", "LONG"
        else:
            regime, bias = "TRENDING_DOWN", "SHORT"
    elif atr_pct > 3:
        regime, bias = "VOLATILE", "REDUCE"
    else:
        regime, bias = "RANGING", "MEAN_REVERSION"

    high_20 = np.max(highs[-20:])
    if closes[-1] >= high_20 * 0.99:
        regime, bias = "BREAKOUT", "LONG"

    return {"regime": regime, "bias": bias, "adx": adx, "atr_pct": atr_pct}


def _regime_adjustment(regime: str, bias: str, direction: str) -> float:
    """Calculate regime adjustment for a signal direction"""
    if regime == "TRENDING_UP" and direction == "LONG":
        return 10.0
    elif regime == "TRENDING_DOWN" and direction == "SHORT":
        return 10.0
    elif regime == "TRENDING_UP" and direction == "SHORT":
        return -10.0
    elif regime == "TRENDING_DOWN" and direction == "LONG":
        return -10.0
    elif regime == "BREAKOUT" and direction == "LONG":
        return 8.0
    elif regime == "VOLATILE":
        return -5.0
    elif regime == "RANGING":
        return -3.0
    return 0.0


def _check_mtf_alignment(symbol: str) -> Dict:
    """Check multi-timeframe alignment (15m + 1h + 4h)"""
    directions = {}
    scores = {}
    for tf_label, tf_api in [("15m", "Min15"), ("1h", "Min60"), ("4h", "Hour4")]:
        ohlcv = _fetch_ohlcv(symbol, tf_api, 100)
        if not ohlcv or len(ohlcv) < 50:
            continue
        analysis = _full_analysis(ohlcv)
        if "error" not in analysis:
            directions[tf_label] = analysis["direction"]
            scores[tf_label] = analysis["composite_score"]

    if not directions:
        return {"aligned": False, "bonus": 0, "directions": {}}

    non_neutral = [d for d in directions.values() if d != "NEUTRAL"]
    if len(non_neutral) >= 2 and len(set(non_neutral)) == 1:
        aligned = True
        bonus = 10 if len(non_neutral) == 3 else 5
    else:
        aligned = False
        bonus = 0

    return {
        "aligned": aligned,
        "bonus": bonus,
        "directions": directions,
        "scores": scores,
    }


def _send_telegram(message: str) -> bool:
    """Send Telegram alert (raw, no @tool)"""
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        return False
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
        return result.get('ok', False)
    except:
        return False


def _format_alert(symbol: str, data: Dict) -> str:
    """Format HTML alert for Telegram"""
    direction_emoji = "🟢" if data['direction'] == "LONG" else "🔴"

    # AI consensus info
    ai = data.get('ai_consensus', {})
    ai_votes = ai.get('votes', {})
    ai_details = ai.get('details', [])
    ai_line = ""
    if ai_details:
        vote_parts = []
        for v in ai_details:
            icon = "✅" if v['status'] == 'OK' else "❌"
            vote_parts.append(f"{icon}{v['name']}: {v['direction']}")
        ai_line = f"\n<b>AI Votes:</b> {' | '.join(vote_parts)}\n"

    return (
        f"{direction_emoji} <b>TradeOracle Signal</b>\n"
        f"━━━━━━━━━━━━━━━\n"
        f"<b>{symbol}</b> | {data['direction']}\n"
        f"Score: <b>{data['weighted_score']:.0f}</b>/100 | Conf: {data['confidence']}%\n\n"
        f"Entry: <code>${data['entry_price']:.6g}</code>\n"
        f"TP1: <code>${data['tp1']:.6g}</code>\n"
        f"TP2: <code>${data['tp2']:.6g}</code>\n"
        f"TP3: <code>${data['tp3']:.6g}</code>\n"
        f"SL: <code>${data['sl']:.6g}</code>\n\n"
        f"RSI: {data['rsi']:.1f} | EMA: {data['ema_status']}\n"
        f"Regime: {data.get('regime', 'N/A')}\n"
        f"{ai_line}"
        f"━━━━━━━━━━━━━━━\n"
        f"<i>Domino Pipeline v2.0 (5 AI)</i>"
    )


def run_domino(min_score: int = 70, top_n: int = 5,
               alert_threshold: int = 75) -> Dict:
    """
    Run the complete Domino Pipeline.
    1 call = Scan -> Filter -> Regime -> Analyze -> Score -> Signal -> Alert

    Args:
        min_score: Minimum scan score to pass filter (0-100)
        top_n: Max symbols to deep-analyze
        alert_threshold: Min weighted_score to send Telegram alert
    Returns:
        Dict with run_id, scanned count, regime, analyses, signals, alerts
    """
    start_ms = time.time()

    # === STEP 0: Init DB run ===
    run_id = create_pipeline_run()

    try:
        # === STEP 1: SCAN ===
        tickers = _fetch_mexc_tickers()
        if not tickers:
            complete_pipeline_run(run_id, "FAILED", int((time.time() - start_ms) * 1000))
            return {"run_id": run_id, "error": "Failed to fetch MEXC tickers"}

        min_volume = SCANNER_CONFIG.get("min_volume_24h", 100000)
        scored = []

        for t in tickers:
            if not t.get('symbol', '').endswith('_USDT'):
                continue

            symbol_raw = t['symbol']
            symbol = symbol_raw.replace('_USDT', '/USDT')
            price = float(t.get('lastPrice') or 0)
            high24 = float(t.get('high24Price') or price * 1.05) if t.get('high24Price') else price * 1.05
            low24 = float(t.get('low24Price') or price * 0.95) if t.get('low24Price') else price * 0.95
            change = float(t.get('riseFallRate') or 0) * 100
            volume = float(t.get('amount24') or 0)

            if price <= 0 or volume < min_volume:
                continue

            # Range position
            range_24h = high24 - low24
            if range_24h > 0 and range_24h / price < 0.5:
                position = (price - low24) / range_24h
            else:
                position = 0.5 + (change / 100) if abs(change) < 50 else 0.5
            position = max(0.0, min(1.0, position))

            volatility = (range_24h / price * 100) if price > 0 else 0

            # Composite scan score (same logic as market_scanner)
            scan_score = 30

            if volume > 0:
                vol_log = math.log10(volume)
                if vol_log >= 10:
                    scan_score += 25
                elif vol_log >= 9:
                    scan_score += 20
                elif vol_log >= 8:
                    scan_score += 15
                elif vol_log >= 7:
                    scan_score += 10
                elif vol_log >= 6:
                    scan_score += 5

            if position >= 0.95:
                scan_score += 25
            elif position >= 0.85:
                scan_score += 20
            elif position >= 0.70:
                scan_score += 10
            elif position <= 0.05:
                scan_score += 22
            elif position <= 0.15:
                scan_score += 18
            elif position <= 0.30:
                scan_score += 8

            abs_change = abs(change)
            if abs_change >= 20:
                scan_score += 20
            elif abs_change >= 10:
                scan_score += 15
            elif abs_change >= 5:
                scan_score += 10
            elif abs_change >= 2:
                scan_score += 5

            if volatility >= 15:
                scan_score += 10
            elif volatility >= 8:
                scan_score += 5

            if position >= 0.90 and change > 0 and volume > 50_000_000:
                scan_score += 10
            elif position <= 0.10 and volume > 50_000_000:
                scan_score += 8

            scan_score = min(100, scan_score)

            if scan_score >= min_score:
                scored.append({
                    'symbol': symbol,
                    'symbol_raw': symbol_raw,
                    'price': price,
                    'scan_score': scan_score,
                    'change': change,
                    'volume': volume,
                    'position': position,
                })

        total_scanned = len([t for t in tickers if t.get('symbol', '').endswith('_USDT')])
        scored.sort(key=lambda x: (x['scan_score'], x['volume']), reverse=True)
        top_symbols = scored[:top_n]

        # === STEP 2: REGIME ===
        btc_ohlcv = _fetch_ohlcv("BTC/USDT", "Hour4", 100)
        regime_data = _detect_regime(btc_ohlcv)
        regime = regime_data["regime"]
        regime_bias = regime_data["bias"]

        # === STEP 3: ANALYZE each symbol ===
        analyses = []
        for sym_data in top_symbols:
            symbol = sym_data['symbol']

            ohlcv_1h = _fetch_ohlcv(symbol, "Min60", 100)
            if not ohlcv_1h or len(ohlcv_1h) < 50:
                continue

            ta = _full_analysis(ohlcv_1h)
            if "error" in ta:
                continue

            # MTF alignment check
            mtf = _check_mtf_alignment(symbol)

            # Regime adjustment
            reg_adj = _regime_adjustment(regime, regime_bias, ta["direction"])

            # === STEP 3.5: AI CONSENSUS (3 LM Studio + Gemini) ===
            ai_data = {
                'price': ta['price'], 'rsi': ta['rsi'],
                'macd_histogram': ta['macd']['histogram'],
                'ema_status': ta['ema_status'], 'obv_trend': ta['obv_trend'],
                'bb_squeeze': ta['bollinger']['in_squeeze'],
                'stoch_k': ta['stochastic']['k'],
                'scan_score': sym_data['scan_score'],
                'technical_score': ta['composite_score'],
                'regime': regime,
            }
            consensus = run_ai_consensus(symbol, ai_data, timeout=45)
            ai_score = consensus["consensus_confidence"]

            # Save AI votes to DB
            save_ai_votes(run_id, symbol, consensus.get("details", []))

            # Override direction if AI consensus is strong and disagrees
            ai_dir = consensus["consensus_direction"]
            if consensus["models_ok"] >= 3 and ai_score >= 70 and ai_dir != "NEUTRAL":
                final_direction = ai_dir
            else:
                final_direction = ta["direction"]

            # Weighted score with AI consensus
            weighted = (
                sym_data['scan_score'] * WEIGHTS["scan_score"]
                + ta["composite_score"] * WEIGHTS["technical_score"]
                + reg_adj * WEIGHTS["regime_bonus"]
                + mtf["bonus"] * WEIGHTS["mtf_alignment"]
                + ai_score * WEIGHTS["ai_consensus"]
            )
            weighted = max(0, min(100, weighted))

            # Confidence = weighted score capped
            confidence = int(min(95, weighted))

            analysis = {
                'symbol': symbol,
                'timeframe': '1h',
                'price': ta['price'],
                'rsi': ta['rsi'],
                'macd_histogram': ta['macd']['histogram'],
                'ema_status': ta['ema_status'],
                'obv_trend': ta['obv_trend'],
                'bb_squeeze': ta['bollinger']['in_squeeze'],
                'stoch_k': ta['stochastic']['k'],
                'patterns': ta['patterns'],
                'scan_score': sym_data['scan_score'],
                'technical_score': ta['composite_score'],
                'regime_adjustment': reg_adj,
                'weighted_score': weighted,
                'direction': final_direction,
                'entry_price': ta['entry'],
                'tp1': ta['tp1'],
                'tp2': ta['tp2'],
                'tp3': ta['tp3'],
                'sl': ta['sl'],
                'confidence': confidence,
                'promoted_to_signal': 0,
                'regime': regime,
                'mtf': mtf,
                'ai_consensus': consensus,
            }
            analyses.append(analysis)

            # Save to DB
            save_pipeline_analysis(run_id, analysis)

        # === STEP 4: SIGNAL (promote best) ===
        analyses.sort(key=lambda x: x['weighted_score'], reverse=True)
        promoted = []
        for a in analyses:
            if a['direction'] == "NEUTRAL":
                continue
            if a['weighted_score'] >= min_score:
                signal_id = save_signal(
                    symbol=a['symbol'],
                    direction=a['direction'],
                    score=int(a['weighted_score']),
                    price=a['entry_price'],
                    tp1=a['tp1'], tp2=a['tp2'], tp3=a['tp3'], sl=a['sl'],
                    reasons=json.dumps(a['patterns']),
                    timeframe='1h',
                    confidence=a['confidence'],
                    agent_reasoning=f"Domino Pipeline run#{run_id} | Scan:{a['scan_score']} Tech:{a['technical_score']} Regime:{a['regime_adjustment']:+.0f} MTF:{a['mtf']['bonus']}"
                )
                a['promoted_to_signal'] = 1
                a['signal_id'] = signal_id
                promoted.append(a)

        # === STEP 5: ALERT ===
        alerts_sent = 0
        for p in promoted:
            if p['confidence'] >= alert_threshold:
                msg = _format_alert(p['symbol'], p)
                if _send_telegram(msg):
                    alerts_sent += 1

        # === FINALIZE ===
        duration_ms = int((time.time() - start_ms) * 1000)
        complete_pipeline_run(
            run_id=run_id,
            status="COMPLETED",
            duration_ms=duration_ms,
            total_scanned=total_scanned,
            signals_found=len(promoted),
            top_symbols=[s['symbol'] for s in top_symbols],
            regime=regime,
            regime_bias=regime_bias,
        )

        return {
            "run_id": run_id,
            "status": "COMPLETED",
            "scanned": total_scanned,
            "filtered": len(scored),
            "analyzed": len(analyses),
            "regime": regime,
            "regime_bias": regime_bias,
            "signals": [
                {
                    "symbol": p['symbol'],
                    "direction": p['direction'],
                    "weighted_score": round(p['weighted_score'], 1),
                    "confidence": p['confidence'],
                    "entry": p['entry_price'],
                    "tp1": p['tp1'], "tp2": p['tp2'], "tp3": p['tp3'],
                    "sl": p['sl'],
                    "ai_consensus": p.get('ai_consensus', {}).get('consensus_direction', 'N/A'),
                    "ai_confidence": p.get('ai_consensus', {}).get('consensus_confidence', 0),
                    "ai_votes": p.get('ai_consensus', {}).get('votes', {}),
                }
                for p in promoted
            ],
            "ai_models_used": len(analyses[0]['ai_consensus']['details']) if analyses and 'ai_consensus' in analyses[0] else 0,
            "alerts_sent": alerts_sent,
            "duration_ms": duration_ms,
        }

    except Exception as e:
        duration_ms = int((time.time() - start_ms) * 1000)
        complete_pipeline_run(run_id, "FAILED", duration_ms)
        return {"run_id": run_id, "status": "FAILED", "error": str(e), "duration_ms": duration_ms}
