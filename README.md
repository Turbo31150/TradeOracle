# TradeOracle - Autonomous Crypto Trading Agent

> **Google Gemini Hackathon 2026** | Built with Gemini 3 + LangChain + Real-Time Market Data

## What is TradeOracle?

TradeOracle is an **autonomous crypto trading intelligence agent** powered by **Google Gemini 3**. It scans **850+ cryptocurrency futures contracts** in real-time, performs deep technical analysis across multiple timeframes, and generates high-confidence trading signals with full **chain-of-thought reasoning**.

Unlike traditional trading bots that follow rigid rules, TradeOracle **thinks through each decision** using Gemini's advanced function-calling capabilities. It autonomously selects which tools to use, gathers real market data, cross-references 14+ technical indicators, and explains its reasoning step by step.

## Key Features

| Feature | Description |
|---------|-------------|
| **Real-Time Market Scanning** | Scans 850+ MEXC Futures contracts with composite scoring (0-100) |
| **Deep Technical Analysis** | RSI, MACD, ATR, Bollinger Bands, Stochastic, OBV, EMA, Fibonacci, candlestick patterns |
| **Multi-Timeframe Alignment** | Cross-references 15m, 1h, and 4h charts for higher-confidence signals |
| **Chain-of-Thought Reasoning** | Gemini explains every decision: context, data, analysis, risk, decision, confidence |
| **Market Regime Detection** | Identifies trending (up/down), ranging, volatile, or breakout conditions via ADX/ATR |
| **Portfolio Monitoring** | Live position tracking with margin health alerts (CRITICAL/DANGER/OK/SAFE/EXCESS) |
| **Telegram Alerts** | Automated notifications for critical trading signals |
| **Signal History** | SQLite database tracking all signals and agent decisions |

## How Gemini 3 Powers TradeOracle

TradeOracle leverages Gemini 3 through **LangChain's tool-calling framework**:

1. **Autonomous Function Calling** - Gemini decides which of the 10 trading tools to invoke based on the user's query
2. **Multi-Step Orchestration** - The agent chains multiple tool calls (scan -> analyze -> compare -> decide) in a single conversation turn
3. **Chain-of-Thought Protocol** - A structured 6-step reasoning framework ensures every recommendation is data-driven:
   - Context (market regime) -> Data Collection (real prices) -> Technical Analysis (14 indicators) -> Risk Assessment -> Decision (entry/TP/SL) -> Confidence Rating
4. **Conversational Memory** - Maintains chat context for follow-up questions and iterative analysis

### Available Tools (10)

| Tool | What It Does |
|------|-------------|
| `scan_market` | Scans 850+ MEXC Futures contracts, returns top opportunities ranked by composite score |
| `get_coin_price` | Fetches current price and 24h statistics for any trading pair |
| `get_top_movers` | Returns top gainers or losers in the last 24 hours |
| `get_ohlcv_data` | Retrieves candlestick data (Open/High/Low/Close/Volume) for any timeframe |
| `analyze_coin_technical` | Deep analysis with 14 indicators + composite score + entry/TP/SL levels |
| `get_market_regime` | Determines market state (trending/ranging/volatile/breakout) using ADX and ATR |
| `multi_timeframe_analysis` | Analyzes 15m + 1h + 4h simultaneously, checks trend alignment |
| `get_positions` | Shows all open positions with PnL, margin ratio, and liquidation distance |
| `check_margin_health` | Identifies at-risk positions and suggests margin transfers |
| `send_telegram_alert` | Sends trading alerts via Telegram bot |

## Architecture

```
                    +------------------+
  User Query -----> |  Streamlit UI    |
                    +--------+---------+
                             |
                    +--------v---------+
                    |  Gemini 3 Agent  |  (LangChain + bind_tools)
                    |  System Prompt:  |
                    |  Trading Oracle  |
                    +--------+---------+
                             |
              +--------------+--------------+
              |              |              |
     +--------v---+  +------v------+  +----v-------+
     | Market Data |  | Technical   |  | Portfolio  |
     | Scanner     |  | Analysis    |  | Manager    |
     | (MEXC API)  |  | (NumPy)     |  | (Auth API) |
     +-------------+  +-------------+  +------------+
              |              |              |
     +--------v--------------v--------------v--------+
     |              SQLite Database                   |
     |         (signals + decisions history)          |
     +------------------------------------------------+
```

## Quick Start

### Prerequisites

- **Python 3.10+** (tested with 3.12)
- **Google Gemini API key** (free at [aistudio.google.com/apikey](https://aistudio.google.com/apikey))

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/YOUR_USERNAME/TradeOracle.git
cd TradeOracle

# 2. Create a virtual environment (recommended)
python -m venv venv

# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure your API keys
cp .env.example .env
# Edit .env and add your GOOGLE_API_KEY (required)
# Optionally add MEXC and Telegram keys for full features
```

### Launch

```bash
streamlit run app.py
```

The app will open in your browser at `http://localhost:8501`.

### API Key Setup

| Key | Required? | Where to Get It | What It Enables |
|-----|-----------|-----------------|-----------------|
| `GOOGLE_API_KEY` | **Yes** | [aistudio.google.com/apikey](https://aistudio.google.com/apikey) | Gemini 3 agent (core functionality) |
| `MEXC_ACCESS_KEY` + `MEXC_SECRET_KEY` | No | [mexc.com/user/openapi](https://www.mexc.com/user/openapi) | Position tracking, margin health |
| `TELEGRAM_TOKEN` + `TELEGRAM_CHAT_ID` | No | [@BotFather](https://t.me/BotFather) on Telegram | Alert notifications |

**Note:** Market scanning, price checking, technical analysis, and market regime detection all work **without any exchange API keys** - they use public MEXC data endpoints. Only position tracking and margin health require authenticated MEXC keys.

## Example Queries

Try these in the chat interface:

- **"Scan the market and find the top 5 breakout opportunities"** - Full market scan with composite scoring
- **"Analyze BTC/USDT with multi-timeframe analysis"** - 15m + 1h + 4h cross-reference
- **"What's the current market regime?"** - ADX/ATR-based regime detection
- **"Show me the top gainers and losers today"** - 24h movers on MEXC Futures
- **"Is ETH/USDT a good long entry right now?"** - Full technical analysis with entry/TP/SL
- **"Check my position margin health"** - Position risk assessment (requires MEXC keys)

## Project Structure

```
TradeOracle/
├── app.py                          # Streamlit web interface
├── agent/
│   └── gemini_agent.py             # Gemini 3 agent with tool calling
├── tools/
│   ├── market_scanner.py           # MEXC market scanning (850+ contracts)
│   ├── technical_analysis.py       # 14 technical indicators + patterns
│   ├── portfolio.py                # Position tracking + margin health
│   └── alerts.py                   # Telegram notifications
├── database/
│   └── signals_db.py               # SQLite signal/decision storage
├── config/
│   └── settings.py                 # Environment configuration
├── .env.example                    # API key template
├── requirements.txt                # Python dependencies
└── README.md                       # This file
```

## Technical Details

### Composite Scoring Algorithm

The market scanner uses a multi-factor composite scoring system (0-100):

- **Volume** (0-25 pts) - Log-scale volume analysis (whale/mega/high/med)
- **Range Position** (0-25 pts) - Price position within 24h range (breakout zone >95%, reversal zone <5%)
- **Momentum** (0-20 pts) - 24h price change magnitude
- **Volatility** (0-10 pts) - Range as percentage of price
- **Confluence** (0-10 pts) - Multiple factors confirming the signal

### Technical Indicators

All indicators are calculated from raw OHLCV data using NumPy (no external TA libraries):

- **RSI** (14-period) - Relative Strength Index with Wilder smoothing
- **MACD** (12/26/9) - Moving Average Convergence Divergence with crossover detection
- **ATR** (14-period) - Average True Range for volatility
- **Bollinger Bands** (20-period, 2 std) - With squeeze detection
- **Stochastic** (14-period) - %K and %D values
- **OBV** - On-Balance Volume with 20-period MA trend
- **EMA** (5/10/20) - Exponential Moving Average alignment detection
- **Fibonacci** - Retracement levels from swing high/low
- **Candlestick Patterns** - Doji, Hammer, Engulfing patterns

### Market Regime Detection

Uses ADX (Average Directional Index) and ATR to classify market conditions:

| Regime | Condition | Trading Bias |
|--------|-----------|-------------|
| Trending Up | ADX > 25, +DI > -DI | Long / Trend-following |
| Trending Down | ADX > 25, -DI > +DI | Short / Trend-following |
| Ranging | ADX < 25, Low ATR | Mean reversion |
| Volatile | High ATR% | Reduce position size |
| Breakout | Price near 20-period high | Long / Breakout strategies |

## Tech Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| AI Engine | Google Gemini 3 (`gemini-2.5-flash`) | Reasoning, tool selection, response generation |
| Agent Framework | LangChain (`bind_tools`) | Tool calling orchestration |
| Market Data | MEXC Futures API | 850+ contracts, real-time prices, OHLCV |
| Technical Analysis | NumPy | All 14 indicators computed from raw data |
| Frontend | Streamlit | Interactive web UI with chat interface |
| Database | SQLite | Signal and decision history |
| Alerts | Telegram Bot API | Trading notifications |

## Disclaimer

TradeOracle is a **research and educational tool** built for the Google Gemini Hackathon. It is **NOT financial advice**. Cryptocurrency trading involves significant risk. Always do your own research and never trade with money you cannot afford to lose.

## License

MIT License - Built for the Google Gemini Hackathon 2026
