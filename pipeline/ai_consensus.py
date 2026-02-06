"""
TradeOracle - AI Consensus Module (Hardened v2.0)
Queries 3 LM Studio servers + Gemini in parallel for trade validation.
Features: Retry with backoff, keyword fallback, graceful degradation.
"""
import json
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional

from config.settings import (
    LM_STUDIO_M1_URL, LM_STUDIO_M2_URL, LM_STUDIO_M3_URL,
    GOOGLE_API_KEY
)

# Model assignments per server (gpt-oss-20b = most reliable JSON responder)
LM_MODELS = {
    "M1_gptoss": {"url": LM_STUDIO_M1_URL, "model": "openai/gpt-oss-20b"},
    "M2_gptoss": {"url": LM_STUDIO_M2_URL, "model": "openai/gpt-oss-20b"},
    "M3_gptoss": {"url": LM_STUDIO_M3_URL, "model": "openai/gpt-oss-20b"},
}

# Models that don't support system prompts
NO_SYSTEM = {"mistral-7b-instruct-v0.3", "phi-3.1-mini-128k-instruct"}


def _build_trade_prompt(symbol: str, data: Dict) -> str:
    """Build a concise trade analysis prompt from technical data"""
    return (
        f"Analyze {symbol} for a trade signal.\n"
        f"Price: ${data.get('price', 0):.6g}\n"
        f"RSI(14): {data.get('rsi', 0):.1f}\n"
        f"MACD Histogram: {data.get('macd_histogram', 0):.6g}\n"
        f"EMA Alignment: {data.get('ema_status', 'N/A')}\n"
        f"OBV Trend: {data.get('obv_trend', 'N/A')}\n"
        f"Bollinger Squeeze: {data.get('bb_squeeze', False)}\n"
        f"Stochastic %K: {data.get('stoch_k', 0):.1f}\n"
        f"Scan Score: {data.get('scan_score', 0)}/100\n"
        f"Technical Score: {data.get('technical_score', 0)}/100\n"
        f"Market Regime: {data.get('regime', 'N/A')}\n\n"
        f"Based on these indicators, what is your trade recommendation?\n"
        f"IMPORTANT: Respond with ONLY a raw JSON object, no markdown, no text before or after:\n"
        f'{{"direction": "LONG", "confidence": 75, "reason": "brief explanation"}}\n'
        f"direction must be LONG, SHORT, or NEUTRAL. confidence must be 0-100."
    )


def _parse_ai_response(content: str) -> Optional[Dict]:
    """Robust JSON extraction with fallbacks"""
    if not content:
        return None

    # Strip markdown code blocks
    if "```" in content:
        parts = content.split("```")
        for part in parts[1:]:
            cleaned = part.strip()
            if cleaned.startswith("json"):
                cleaned = cleaned[4:].strip()
            if '{' in cleaned:
                content = cleaned
                break

    # Try JSON extraction
    start = content.find('{')
    end = content.rfind('}')
    if start >= 0 and end > start:
        try:
            parsed = json.loads(content[start:end+1])
            d = str(parsed.get("direction", "NEUTRAL")).upper()
            if d in ("LONG", "SHORT", "NEUTRAL"):
                return {
                    "direction": d,
                    "confidence": min(100, max(0, int(parsed.get("confidence", 50)))),
                    "reason": str(parsed.get("reason", ""))[:200],
                    "method": "json",
                }
        except (json.JSONDecodeError, ValueError, TypeError):
            pass

    # Keyword fallback
    cl = content.lower()
    if "short" in cl and "long" not in cl:
        return {"direction": "SHORT", "confidence": 55, "reason": content[:80], "method": "keyword"}
    elif "long" in cl and "short" not in cl:
        return {"direction": "LONG", "confidence": 55, "reason": content[:80], "method": "keyword"}
    elif "neutral" in cl or "wait" in cl:
        return {"direction": "NEUTRAL", "confidence": 40, "reason": content[:80], "method": "keyword"}

    return None


def _query_lm_studio(name: str, config: Dict, prompt: str, timeout: int = 30) -> Dict:
    """Query a single LM Studio server with retry"""
    t0 = time.time()
    last_error = ""

    for attempt in range(2):  # 1 retry
        try:
            url = f"{config['url']}/v1/chat/completions"
            model = config['model']

            messages = []
            if model not in NO_SYSTEM:
                messages.append({
                    "role": "system",
                    "content": "You are a crypto trading analyst. Respond ONLY with valid JSON."
                })
            messages.append({"role": "user", "content": prompt})

            payload = json.dumps({
                "model": model,
                "messages": messages,
                "temperature": 0.1,
                "max_tokens": 150,
            }).encode()

            req = urllib.request.Request(
                url, data=payload,
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                result = json.loads(resp.read())

            content = result['choices'][0]['message']['content'].strip()
            elapsed_ms = int((time.time() - t0) * 1000)

            parsed = _parse_ai_response(content)
            if parsed:
                return {
                    "name": name, "model": model,
                    "direction": parsed["direction"],
                    "confidence": parsed["confidence"],
                    "reason": parsed["reason"],
                    "elapsed_ms": elapsed_ms,
                    "status": "OK",
                    "method": parsed["method"],
                }

            return {
                "name": name, "model": model,
                "direction": "NEUTRAL", "confidence": 30,
                "reason": f"Unparseable: {content[:100]}",
                "elapsed_ms": elapsed_ms, "status": "PARSE_ERROR",
            }

        except Exception as e:
            last_error = str(e)[:100]
            if attempt < 1:
                time.sleep(1)

    elapsed_ms = int((time.time() - t0) * 1000)
    return {
        "name": name, "model": config['model'],
        "direction": "NEUTRAL", "confidence": 0,
        "reason": last_error,
        "elapsed_ms": elapsed_ms, "status": "ERROR",
    }


def _query_gemini(prompt: str, timeout: int = 15) -> Dict:
    """Query Gemini with retry + exponential backoff"""
    t0 = time.time()
    last_error = ""

    for attempt in range(3):  # 2 retries
        try:
            import google.generativeai as genai
            genai.configure(api_key=GOOGLE_API_KEY)
            model = genai.GenerativeModel("gemini-2.5-flash")

            resp = model.generate_content(prompt)
            elapsed_ms = int((time.time() - t0) * 1000)
            content = resp.text.strip()

            parsed = _parse_ai_response(content)
            if parsed:
                return {
                    "name": "Gemini_Flash", "model": "gemini-2.5-flash",
                    "direction": parsed["direction"],
                    "confidence": parsed["confidence"],
                    "reason": parsed["reason"],
                    "elapsed_ms": elapsed_ms,
                    "status": "OK",
                    "method": parsed["method"],
                }

            return {
                "name": "Gemini_Flash", "model": "gemini-2.5-flash",
                "direction": "NEUTRAL", "confidence": 30,
                "reason": f"Unparseable: {content[:100]}",
                "elapsed_ms": elapsed_ms, "status": "PARSE_ERROR",
            }

        except Exception as e:
            last_error = str(e)[:100]
            if "429" in last_error or "quota" in last_error.lower():
                wait = 2 ** (attempt + 1)  # 2s, 4s, 8s
                time.sleep(wait)
            elif attempt < 2:
                time.sleep(1)

    elapsed_ms = int((time.time() - t0) * 1000)
    return {
        "name": "Gemini_Flash", "model": "gemini-2.5-flash",
        "direction": "NEUTRAL", "confidence": 0,
        "reason": last_error,
        "elapsed_ms": elapsed_ms, "status": "ERROR",
    }


def run_ai_consensus(symbol: str, technical_data: Dict,
                     timeout: int = 45) -> Dict:
    """
    Run AI consensus: 3 LM Studio + 1 Gemini in parallel.
    Hardened: retry, backoff, fallback, graceful degradation.
    """
    prompt = _build_trade_prompt(symbol, technical_data)
    votes = []
    t0 = time.time()

    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {}

        for name, config in LM_MODELS.items():
            f = executor.submit(_query_lm_studio, name, config, prompt, timeout)
            futures[f] = name

        if GOOGLE_API_KEY:
            f = executor.submit(_query_gemini, prompt, timeout)
            futures[f] = "Gemini_Flash"

        try:
            for future in as_completed(futures, timeout=timeout + 10):
                try:
                    result = future.result(timeout=5)
                    votes.append(result)
                except Exception as e:
                    votes.append({
                        "name": futures[future], "model": "unknown",
                        "direction": "NEUTRAL", "confidence": 0,
                        "reason": f"Future error: {e}", "status": "TIMEOUT",
                    })
        except TimeoutError:
            # Some futures didn't complete - add TIMEOUT entries for unfinished
            completed_names = {v["name"] for v in votes}
            for f, name in futures.items():
                if name not in completed_names:
                    votes.append({
                        "name": name, "model": "unknown",
                        "direction": "NEUTRAL", "confidence": 0,
                        "reason": "Global timeout exceeded",
                        "elapsed_ms": int((time.time() - t0) * 1000),
                        "status": "TIMEOUT",
                    })

    total_ms = int((time.time() - t0) * 1000)

    # Tally votes
    direction_counts = {"LONG": 0, "SHORT": 0, "NEUTRAL": 0}
    confidence_sum = {"LONG": 0, "SHORT": 0, "NEUTRAL": 0}
    ok_votes = [v for v in votes if v["status"] == "OK"]

    for v in votes:
        d = v.get("direction", "NEUTRAL")
        if d in direction_counts:
            direction_counts[d] += 1
            confidence_sum[d] += v.get("confidence", 0)

    # Determine consensus
    if direction_counts["LONG"] > direction_counts["SHORT"] and direction_counts["LONG"] > direction_counts["NEUTRAL"]:
        consensus_dir = "LONG"
    elif direction_counts["SHORT"] > direction_counts["LONG"] and direction_counts["SHORT"] > direction_counts["NEUTRAL"]:
        consensus_dir = "SHORT"
    else:
        consensus_dir = "NEUTRAL"

    winning_count = direction_counts[consensus_dir]
    avg_confidence = int(confidence_sum[consensus_dir] / winning_count) if winning_count > 0 else 0

    # Unanimity bonus
    if winning_count == len(ok_votes) and len(ok_votes) >= 2 and consensus_dir != "NEUTRAL":
        avg_confidence = min(95, avg_confidence + 10)

    return {
        "consensus_direction": consensus_dir,
        "consensus_confidence": avg_confidence,
        "votes": direction_counts,
        "models_ok": len(ok_votes),
        "models_total": len(votes),
        "details": votes,
        "total_ms": total_ms,
    }
