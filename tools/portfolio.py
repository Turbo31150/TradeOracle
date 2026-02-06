"""
TradeOracle - Portfolio & Position Management Tools
Extracted from Trading MCP Ultimate v3.7
MEXC Futures position tracking + margin health
"""
import json
import time
import hashlib
import hmac
import urllib.request
import urllib.parse
from typing import Dict
from langchain_core.tools import tool

from config.settings import MEXC_ACCESS_KEY, MEXC_SECRET_KEY


def _mexc_authenticated_request(endpoint: str) -> Dict:
    """Make authenticated request to MEXC Futures API"""
    if not MEXC_ACCESS_KEY or not MEXC_SECRET_KEY:
        return {"success": False, "error": "MEXC API keys not configured. Set MEXC_ACCESS_KEY and MEXC_SECRET_KEY in .env"}

    try:
        timestamp = str(int(time.time() * 1000))
        params = f'timestamp={timestamp}'
        signature = hmac.new(
            MEXC_SECRET_KEY.encode(),
            params.encode(),
            hashlib.sha256
        ).hexdigest()

        url = f'https://contract.mexc.com/api/v1/private/{endpoint}?{params}&signature={signature}'
        req = urllib.request.Request(url)
        req.add_header('Content-Type', 'application/json')
        req.add_header('ApiKey', MEXC_ACCESS_KEY)

        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read())
    except Exception as e:
        return {"success": False, "error": str(e)}


@tool
def get_positions() -> str:
    """Get all currently open positions on MEXC Futures exchange.
    Shows symbol, direction, entry price, unrealized PnL, margin ratio, and liquidation distance.
    """
    data = _mexc_authenticated_request("position/open_positions")
    if not data.get('data'):
        if "error" in data:
            return f"Error: {data['error']}"
        return "No open positions on MEXC Futures."

    positions = []
    for p in data['data']:
        symbol = p.get('symbol', '').replace('_USDT', '/USDT')
        direction = 'LONG' if p.get('positionType', 1) == 1 else 'SHORT'
        entry = float(p.get('openAvgPrice', 0))
        margin_ratio = float(p.get('marginRatio', 0)) * 100
        pnl = float(p.get('unrealisedPnl', 0))
        margin = float(p.get('positionMargin', 0))
        liq_price = float(p.get('liquidatePrice', 0))
        size = float(p.get('holdVol', 0))
        leverage = int(p.get('leverage', 0))

        # Margin status
        if margin_ratio < 5:
            status = "CRITICAL"
        elif margin_ratio < 8:
            status = "DANGER"
        elif margin_ratio < 12:
            status = "OK"
        elif margin_ratio < 20:
            status = "SAFE"
        else:
            status = "EXCESS"

        # Distance to liquidation
        if liq_price > 0 and entry > 0:
            if direction == 'LONG':
                dist = ((entry - liq_price) / entry) * 100
            else:
                dist = ((liq_price - entry) / entry) * 100
        else:
            dist = 0

        positions.append({
            'symbol': symbol,
            'direction': direction,
            'entry': entry,
            'pnl': pnl,
            'margin_ratio': margin_ratio,
            'margin': margin,
            'status': status,
            'liq_price': liq_price,
            'liq_distance': dist,
            'size': size,
            'leverage': leverage,
        })

    positions.sort(key=lambda x: x['margin_ratio'])

    result = f"OPEN POSITIONS ({len(positions)}):\n{'='*50}\n\n"
    total_pnl = 0
    total_margin = 0

    for p in positions:
        emoji = {"CRITICAL": "[!!!]", "DANGER": "[!]", "OK": "[OK]", "SAFE": "[+]", "EXCESS": "[++]"}.get(p['status'], "")
        result += (
            f"{emoji} {p['symbol']} {p['direction']} x{p['leverage']}\n"
            f"   Entry: ${p['entry']:.6g} | PnL: ${p['pnl']:.2f}\n"
            f"   Margin: ${p['margin']:.2f} | Ratio: {p['margin_ratio']:.1f}% ({p['status']})\n"
            f"   Liquidation: ${p['liq_price']:.6g} (distance: {p['liq_distance']:.1f}%)\n\n"
        )
        total_pnl += p['pnl']
        total_margin += p['margin']

    result += f"TOTALS: PnL: ${total_pnl:.2f} | Margin Used: ${total_margin:.2f}\n"
    critical = [p for p in positions if p['status'] in ['CRITICAL', 'DANGER']]
    if critical:
        result += f"\nWARNING: {len(critical)} position(s) at risk!\n"

    return result


@tool
def check_margin_health() -> str:
    """Check margin health of all open positions and identify any at-risk positions.
    Returns margin ratios with status (CRITICAL/DANGER/OK/SAFE/EXCESS) and suggestions.
    """
    data = _mexc_authenticated_request("position/open_positions")
    if not data.get('data'):
        if "error" in data:
            return f"Error: {data['error']}"
        return "No open positions - margin health check not needed."

    positions = []
    for p in data['data']:
        ratio = float(p.get('marginRatio', 0)) * 100
        symbol = p.get('symbol', '').replace('_USDT', '/USDT')
        pnl = float(p.get('unrealisedPnl', 0))

        if ratio < 5:
            status = "CRITICAL"
        elif ratio < 8:
            status = "DANGER"
        elif ratio < 12:
            status = "OK"
        elif ratio < 20:
            status = "SAFE"
        else:
            status = "EXCESS"

        positions.append({"symbol": symbol, "ratio": ratio, "status": status, "pnl": pnl})

    positions.sort(key=lambda x: x['ratio'])

    result = "MARGIN HEALTH CHECK:\n\n"
    for p in positions:
        result += f"  {p['symbol']}: {p['ratio']:.1f}% ({p['status']}) | PnL: ${p['pnl']:.2f}\n"

    critical = [p for p in positions if p['status'] in ['CRITICAL', 'DANGER']]
    excess = [p for p in positions if p['status'] == 'EXCESS']

    if critical:
        result += f"\nALERT: {len(critical)} position(s) need attention:\n"
        for c in critical:
            result += f"  -> {c['symbol']}: ADD MARGIN URGENTLY (ratio: {c['ratio']:.1f}%)\n"

    if critical and excess:
        result += "\nSuggested transfers:\n"
        for i, c in enumerate(critical):
            if i < len(excess):
                result += f"  Transfer margin from {excess[i]['symbol']} -> {c['symbol']}\n"

    if not critical:
        result += "\nAll positions healthy - no action needed.\n"

    return result
