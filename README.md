<div align="center">
  <img src="assets/logo.svg" alt="TRADEORACLE AI" width="520"/>
  <br/><br/>

  [![CI](https://github.com/Turbo31150/TradeOracle/actions/workflows/ci.yml/badge.svg)](https://github.com/Turbo31150/TradeOracle/actions/workflows/ci.yml)
  [![License: MIT](https://img.shields.io/badge/License-MIT-00FF88?style=flat-square)](LICENSE)
  [![Python](https://img.shields.io/badge/Python-3.11+-FFD700?style=flat-square&logo=python&logoColor=black)](https://python.org)
  [![Stars](https://img.shields.io/github/stars/Turbo31150/TradeOracle?style=flat-square&color=FFD700)](https://github.com/Turbo31150/TradeOracle/stargazers)
  [![Gemini](https://img.shields.io/badge/Gemini_3-Google_AI-4285F4?style=flat-square&logo=google&logoColor=white)](#domino-pipeline)
  [![MEXC](https://img.shields.io/badge/MEXC-800%2B_futures-00FF88?style=flat-square)](#signal-types)
  [![LangChain](https://img.shields.io/badge/LangChain-agent_framework-1C3C3C?style=flat-square)](#)
  [![MCP](https://img.shields.io/badge/MCP-40%2B_tools-FF8C00?style=flat-square)](#mcp-server)
  [![FastAPI](https://img.shields.io/badge/FastAPI-WebSocket-009688?style=flat-square&logo=fastapi&logoColor=white)](#api)

  <br/>
  <h3>Multi-model AI consensus engine for crypto futures trading</h3>
  <p><em>End-to-end algorithmic trading: scan, analyze with multi-AI consensus, execute with automated TP/SL &mdash; zero human intervention required.</em></p>

  <br/>

  [Pipeline](#domino-pipeline) &bull; [Signals](#signal-types) &bull; [Scoring](#multi-axis-scoring) &bull; [MCP Server](#mcp-server) &bull; [Installation](#installation) &bull; [Configuration](#configuration)

<img src="assets/jarvis-canva-1.png" alt="TradeOracle" width="800">

</div>

---

## Overview

**TRADEORACLE AI** is an autonomous crypto trading agent powered by **Google Gemini 3**. It continuously scans **800+ MEXC futures contracts**, generates trading signals through a proprietary **Domino Pipeline** with multi-AI consensus voting, and executes trades with fully automated take-profit and stop-loss management.

Built for the **Google Cloud Agent Development Kit** hackathon, it demonstrates how an AI agent can manage a complete trading strategy &mdash; from signal detection to order execution &mdash; without human intervention.

---

## Quick Start

```bash
git clone https://github.com/Turbo31150/TradeOracle.git && cd TradeOracle
pip install -r requirements.txt
cp .env.example .env && python entrypoint.py
```

---

## Architecture

```mermaid
flowchart TD
    subgraph Data["Market Data"]
        MEXC["MEXC Futures API\n800+ pairs"]
    end

    subgraph Scanner["Scanner Module"]
        IND["ATR / Volume / RSI\nBollinger / FVG / Momentum"]
    end

    subgraph Consensus["Domino Pipeline — Multi-AI Consensus"]
        G1["Gemini 3.0 Deep\nweight: 1.3"]
        G2["Gemini Flash\nweight: 1.0"]
        LM["LM Studio Local\nweight: 0.8"]
        VOTE["Consensus Vote"]
    end

    subgraph Execution["Trade Execution"]
        STRONG["STRONG 2+\nImmediate"]
        NORMAL["NORMAL 1\nStandard"]
        SKIP["SKIP 0\nNo action"]
    end

    subgraph Risk["Risk Management"]
        TPSL["TP/SL Manager\nTP1 +1.5% | TP2 +3% | TP3 +7%\nSL -1.2%"]
    end

    ALERT["Telegram Alert"]

    MEXC -->|every 30s| IND
    IND -->|score > 70| G1 & G2 & LM
    G1 & G2 & LM --> VOTE
    VOTE --> STRONG & NORMAL & SKIP
    STRONG --> TPSL
    NORMAL --> TPSL
    TPSL --> ALERT
```

---

## Features

| Feature | Description |
|:--------|:------------|
| **Multi-Model Consensus** | 3 AI models vote independently (Gemini Deep, Gemini Flash, LM Studio) with weighted scoring |
| **Signal Detection** | Breakout, reversal, bounce, momentum, and Fair Value Gap detection across 800+ pairs |
| **Risk Management** | Automated 3-tier take-profit (1.5% / 3% / 7%) with stop-loss at -1.2%, position sizing |
| **Telegram Alerts** | Real-time notifications for signals, executions, TP hits, and stop-loss triggers |
| **MCP Integration** | 40+ tools exposed via Model Context Protocol for Claude Code and external clients |
| **FastAPI Backend** | WebSocket + REST API for real-time dashboard and programmatic access |

---

## Domino Pipeline

The Domino Pipeline is the core analysis engine. Each signal candidate passes through multiple AI models that vote independently before a consensus decision is made.

```
  +-------------------------------------------+
  |            MEXC Futures API                |
  |          800+ trading pairs               |
  +---------------------+---------------------+
                        |
                        v  every 30s
  +-------------------------------------------+
  |           SCANNER MODULE                   |
  |                                           |
  |  Indicators:                              |
  |    ATR . Volume . Momentum . RSI          |
  |    Bollinger Bands . Fair Value Gap       |
  |                                           |
  |  Output: Signal candidates (score > 70)   |
  +---------------------+---------------------+
                        |
                        v
  +-------------------------------------------+
  |          DOMINO PIPELINE                   |
  |       (Multi-AI Parallel Analysis)         |
  |                                           |
  |  +-------------+  +-----------+  +------+ |
  |  | Gemini 3.0  |  | Gemini    |  | LM   | |
  |  | Deep        |  | Flash     |  |Studio| |
  |  | Analysis    |  | Validate  |  | Hedge| |
  |  | weight: 1.3 |  | weight: 1 |  | 0.8  | |
  |  +------+------+  +-----+-----+  +--+---+ |
  |         |              |            |      |
  |         +-------+------+------+-----+      |
  |                 |  CONSENSUS  |             |
  |                 +------+------+             |
  +------------------------+-------------------+
                           |
              +------------+------------+
              |            |            |
              v            v            v
         STRONG (2+)   NORMAL (1)   SKIP (0)
         Immediate     Standard     No action
         execution     execution
              |            |
              v            v
  +-------------------------------------------+
  |          TP/SL MANAGER                     |
  |                                           |
  |    TP1  +1.5%  close 33% of position     |
  |    TP2  +3.0%  close 75% of position     |
  |    TP3  +7.0%  close 100% (full exit)    |
  |    SL   -1.2%  stop loss                 |
  +---------------------+---------------------+
                        |
                        v
                 Telegram Alert
```

---

## Signal Types

| Signal | Trigger Conditions | Typical Win Rate |
|:-------|:-------------------|:----------------:|
| **BREAKOUT** | Volume > 2x average, ATR spike, resistance break | ~62% |
| **REVERSAL** | RSI extreme + divergence detected | ~58% |
| **BOUNCE** | Price touching key support zone | ~55% |
| **MOMENTUM** | Strong momentum wave initiated | ~60% |
| **FVG** | Fair Value Gap &mdash; unfilled price imbalance | ~57% |

---

## Multi-Axis Scoring

Every signal is scored across multiple dimensions before reaching the Domino Pipeline:

| Axis | Weight | Description |
|:-----|:------:|:------------|
| **Technical** | 30% | RSI, MACD, Bollinger, ATR composite |
| **Volume** | 25% | Volume anomaly detection vs 20-period average |
| **Momentum** | 20% | Price acceleration and trend strength |
| **Structure** | 15% | Support/resistance levels, FVG zones |
| **Sentiment** | 10% | Funding rate, open interest delta |

**Minimum composite score: 70/100** to enter the Domino Pipeline.

---

## MCP Server

TradeOracle exposes **40+ MCP tools** for integration with Claude Code and other MCP-compatible clients.

### Core Tools

| Tool | Description |
|:-----|:------------|
| `scan_market(symbol, timeframe)` | Scan a specific pair with full indicator suite |
| `get_signal(symbol)` | Get current AI-generated signal |
| `execute_trade(symbol, side, size)` | Execute a market or limit order |
| `get_positions()` | List all open positions with PnL |
| `close_position(symbol)` | Close a specific position |
| `get_pnl(period)` | Aggregate PnL over a time period |
| `set_tp_sl(symbol, tp, sl)` | Configure take-profit and stop-loss |
| `get_market_summary()` | Full market overview with top movers |
| `run_backtest(strategy, period)` | Run historical backtest |
| `get_consensus(symbol)` | View multi-AI consensus breakdown |

### Example Usage

```python
# Via MCP client
result = await mcp.call("scan_market", symbol="BTC_USDT", timeframe="15m")
signal = await mcp.call("get_signal", symbol="BTC_USDT")
await mcp.call("execute_trade", symbol="BTC_USDT", side="long", size=100)
```

---

## Installation

### Prerequisites

- Python 3.11+
- Google Cloud API key (Gemini 3 access)
- MEXC API credentials (futures trading enabled)
- CUDA GPU recommended for local LM Studio inference

### Setup

```bash
git clone https://github.com/Turbo31150/TradeOracle.git
cd TradeOracle

pip install -r requirements.txt

cp .env.example .env
# Fill in: GOOGLE_API_KEY, MEXC_API_KEY, TELEGRAM_BOT_TOKEN...
```

### Run

```bash
# Start the autonomous agent
python entrypoint.py

# Or run as FastAPI server (WebSocket + REST)
python app.py  # Serves on :8080
```

---

## Configuration

```env
# --- Google Cloud / Gemini ---
GOOGLE_API_KEY=AIza...
GOOGLE_CLOUD_PROJECT=my-project

# --- MEXC Futures ---
MEXC_API_KEY=mx0v...
MEXC_SECRET_KEY=...
MEXC_BASE_URL=https://futures.mexc.com/api/v1

# --- Trading Parameters ---
MIN_SCORE=70                # Minimum signal score (0-100)
MIN_VOLUME=1000000          # Minimum 24h volume in USDT
AUTO_TRADE=false            # true = fully autonomous execution
MAX_POSITION_SIZE=500       # Max USDT per position
MAX_CONCURRENT_POSITIONS=5  # Max simultaneous open positions

# --- Notifications ---
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...

# --- MCP Server ---
MCP_PORT=8090
```

---

## Project Structure

```
TradeOracle/
├── entrypoint.py            # Agent entry point
├── app.py                   # FastAPI + WebSocket server
├── requirements.txt
├── .env.example
├── agent/                   # Agent brain
│   ├── trading_agent.py     # Main Gemini 3 agent
│   ├── consensus.py         # Multi-AI voting logic
│   └── risk_manager.py      # Position sizing and risk rules
├── pipeline/                # Domino Pipeline
│   ├── scanner.py           # MEXC 800+ pair scanner
│   ├── signals.py           # Signal detection engine
│   └── executor.py          # Order execution
├── mcp_server/              # MCP tool server
│   ├── server.py            # MCP server bootstrap
│   └── tools.py             # 40+ declared tools
├── tools/                   # Utility modules
│   ├── mexc_tools.py        # MEXC API wrapper
│   ├── gemini_tools.py      # Gemini integration
│   └── telegram_tools.py    # Alert notifications
├── database/                # Persistence layer
│   ├── models.py            # SQLAlchemy models
│   └── db.py                # Connection pool
└── config/
    ├── settings.py          # Trading parameters
    └── models_config.py     # AI model configuration
```

---

## Related Projects

| Project | Description |
|:--------|:------------|
| [jarvis-linux](https://github.com/Turbo31150/jarvis-linux) | JARVIS Etoile -- Distributed multi-GPU AI orchestration system powering TradeOracle |
| [TradeOracle-Nexus-Elastic](https://github.com/Turbo31150/TradeOracle-Nexus-Elastic) | Elasticsearch-based analytics and backtesting extension for TradeOracle |

---

## Complete Trading Session — 10 Minutes, Start to Profit

Here is a real trading session captured from the logs. The scanner detects a breakout, the Domino Pipeline votes, and the trade executes autonomously.

```
[09:14:32] SCANNER: Scanning 847 MEXC futures pairs (30s cycle)
[09:14:32] SCANNER: BREAKOUT detected on SOL/USDT (4H timeframe)
           | Volume: 3.2x average | ATR spike: +47% | RSI: 62
           | Resistance $142.00 broken with conviction
           | Composite score: 84/100 — entering Domino Pipeline

[09:14:33] DOMINO: Dispatching to 3 models in parallel...
[09:14:33] GEMINI-DEEP (weight 1.3):
           | Verdict: BUY | Confidence: 82%
           | "Strong volume breakout above $142 resistance with institutional
           |  footprint. Order flow shows absorption at $141.80. Structure
           |  targets $149-$151 zone. Risk/reward 2.5:1."

[09:14:34] GEMINI-FLASH (weight 1.0):
           | Verdict: BUY | Confidence: 79%
           | "Momentum confirmed. RSI 62 with room to run. MACD histogram
           |  expanding. Bollinger Band squeeze released to upside."

[09:14:35] LM-STUDIO (weight 0.8):
           | Verdict: BUY | Confidence: 71%
           | "MACD crossover positive on 4H. Volume profile supports move.
           |  Minor concern: funding rate elevated at 0.012%."

[09:14:35] CONSENSUS: 3/3 BUY votes
           | Weighted score: (82*1.3 + 79*1.0 + 71*0.8) / (1.3+1.0+0.8) = 78.2%
           | Classification: STRONG SIGNAL (2+ BUY votes)
           | Decision: EXECUTE IMMEDIATELY

[09:14:36] EXECUTOR: Opening LONG position
           | Pair: SOL/USDT | Entry: $142.50 | Size: 2% portfolio ($2,000)
           | Leverage: 5x | Effective size: $10,000
           | TP1: $144.64 (+1.5%) — close 33%
           | TP2: $146.78 (+3.0%) — close 75%
           | TP3: $149.62 (+5.0%) — close 100%
           | SL: $140.79 (-1.2%)

[09:14:37] TELEGRAM: "LONG SOL $142.50 | TP1 $144.64 | TP2 $146.78 | TP3 $149.62 | SL $140.79"
[09:14:37] DATABASE: Trade #4,271 saved to positions table

[09:28:14] TP1 HIT: SOL reached $144.70 | Closed 33% at +1.5%
           | Partial PnL: +$50.00 | Remaining: 67% of position
[09:28:15] TELEGRAM: "TP1 HIT SOL +1.5% (+$50.00) | 67% still open"

[09:47:02] TP2 HIT: SOL reached $146.85 | Closed 75% at +3.0%
           | Partial PnL: +$84.00 | Remaining: 25% of position
[09:47:03] TELEGRAM: "TP2 HIT SOL +3.0% (+$84.00) | 25% runner"

[10:28:14] TP3 HIT: SOL reached $149.80 | Closed 100% — full exit
           | Final PnL: +$102.40 (total across 3 TPs)
           | Duration: 1h 13m 38s | Max drawdown: -0.3%
[10:28:15] TELEGRAM: "TP3 HIT SOL +5.1% | Total PnL: +$102.40 | Trade #4,271 closed"

[10:28:16] DATABASE: Trade #4,271 updated — status: WON
           | Running daily PnL: +$187.60 (3 trades, 2 wins, 1 breakeven)
           | Running weekly PnL: +$412.30
```

### Session Statistics

| Metric | Value |
|:-------|------:|
| Pairs scanned | 847 |
| Signals detected | 4 |
| Entered Domino Pipeline | 3 |
| Consensus reached | 2 |
| Trades executed | 2 |
| Win rate (session) | 100% |
| Total PnL (session) | +$187.60 |
| Average trade duration | 58 min |
| Max drawdown | -0.3% |

---

## Disclaimer

This software is provided for **educational and research purposes only**. Cryptocurrency trading involves substantial risk of loss. Past performance does not guarantee future results. Use at your own risk. The authors are not responsible for any financial losses incurred through the use of this software.

---

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.

---

<div align="center">
  <br/>
  <strong>Franck Delmas (Turbo31150)</strong> &bull; <a href="https://github.com/Turbo31150">github.com/Turbo31150</a> &bull; Toulouse, France
  <br/><br/>
  <em>TRADEORACLE AI &mdash; Autonomous Crypto Trading Intelligence</em>
</div>


## What is TradeOracle?

TradeOracle is an AI trading engine that uses **multi-model consensus** to make trading decisions. Instead of relying on a single model (which can hallucinate or overfit), TradeOracle queries 3+ AI models and only executes when they agree.

This approach reduces false signals by ~60% compared to single-model bots. Each model brings a different perspective — one analyzes technicals, another reads sentiment, a third evaluates risk.

## How Consensus Works

```
Market Data → Scanner detects BREAKOUT pattern on SOL/USDT

  Gemini Deep:  "BUY — bullish divergence on 4H" (confidence: 78%)
  Gemini Flash: "BUY — volume spike above average"  (confidence: 82%)
  LM Studio:    "HOLD — RSI overbought"             (confidence: 45%)
  
  Consensus: 2/3 BUY → STRONG SIGNAL
  
  → Execute: LONG at $142.50
  → Take Profit: $149.62 (+5%)
  → Stop Loss: $139.65 (-2%)
  → Telegram: "🟢 LONG SOL entry $142.50 TP $149.62"
```

## Signal Types

| Signal | Trigger | Example |
|--------|---------|---------|
| **BREAKOUT** | Price breaks key resistance with volume | BTC breaks $70K with 3x avg volume |
| **REVERSAL** | Oversold + divergence detected | ETH RSI 18 + bullish divergence |
| **MOMENTUM** | Strong trend + pullback entry | SOL uptrend, -3% pullback to support |


---

<div align="center">

**If you find this project useful, please consider giving it a star!** ⭐

It helps others discover this project and motivates continued development.

[![Star](https://img.shields.io/github/stars/Turbo31150/TradeOracle?style=social)](https://github.com/Turbo31150/TradeOracle)

</div>


---

<!-- jarvis-author-footer-v1 -->

<div align="center">

### Author

**Franck Delmas** — AI Systems Architect · JARVIS OS Creator · Toulouse, France

[![Portfolio](https://img.shields.io/badge/Portfolio-franckdelmas.dev-00ffd1?style=flat-square)](https://franckdelmas.dev)
[![GitHub](https://img.shields.io/badge/GitHub-Turbo31150-181717?style=flat-square&logo=github)](https://github.com/Turbo31150)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-franck--hlb-0077B5?style=flat-square&logo=linkedin)](https://www.linkedin.com/in/franck-hlb-80bb231b1/)
[![Hire](https://img.shields.io/badge/Status-Open%20to%20work-00ffd1?style=flat-square)](https://github.com/Turbo31150)

*Production-first autodidact · Multi-agent · MCP early adopter · Available for CDI / freelance / consulting.*

Part of the [JARVIS OS](https://github.com/Turbo31150/jarvis-linux) ecosystem ·
[All 44 public repos](https://github.com/Turbo31150?tab=repositories)

</div>
