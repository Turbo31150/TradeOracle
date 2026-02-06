# TradeOracle - Autonomous Crypto Trading Agent

> **Gemini 3 Hackathon 2026** - Built with Google Gemini, LangChain, and Real-Time Market Data

## What is TradeOracle?

TradeOracle is an **autonomous crypto trading intelligence agent** that uses **Gemini 3** as its reasoning engine to analyze 850+ cryptocurrency futures contracts in real-time, perform deep technical analysis, and generate high-confidence trading signals with full chain-of-thought reasoning.

Unlike traditional trading bots that follow rigid rules, TradeOracle **thinks through each decision** using Gemini's advanced reasoning capabilities, cross-referencing multiple technical indicators, timeframes, and market conditions before making recommendations.

## Key Features

- **Real-Time Market Scanning** - Scans 850+ MEXC Futures contracts with composite scoring (0-100)
- **Deep Technical Analysis** - RSI, MACD, ATR, Bollinger Bands, Stochastic, OBV, Fibonacci, candlestick patterns
- **Multi-Timeframe Alignment** - Cross-references 15m, 1h, and 4h charts for higher-confidence signals
- **Chain-of-Thought Reasoning** - Gemini explains every decision step by step
- **Market Regime Detection** - Identifies trending, ranging, volatile, or breakout conditions
- **Portfolio Monitoring** - Live position tracking with margin health alerts
- **Telegram Alerts** - Critical signal notifications via bot

## Gemini 3 Integration

TradeOracle leverages Gemini 3's capabilities through **LangChain's tool-calling agent framework**:

1. **Function Calling** - Gemini autonomously decides which tools to use (scanner, analysis, portfolio)
2. **Chain-of-Thought** - Structured reasoning protocol for every trading decision
3. **Multi-Step Orchestration** - Agent chains multiple tool calls for comprehensive analysis
4. **Natural Language Interface** - Ask questions in plain English, get data-driven answers

## Architecture

```
User Query -> Gemini 3 Agent (LangChain) -> Tool Selection -> Data Retrieval -> Analysis -> Response
                    |
                    v
            10 Trading Tools:
            - scan_market (850+ contracts)
            - get_coin_price
            - get_top_movers
            - get_ohlcv_data
            - analyze_coin_technical (14 indicators)
            - get_market_regime
            - multi_timeframe_analysis
            - get_positions
            - check_margin_health
            - send_telegram_alert
```

## Quick Start

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/tradeoracle-ai.git
cd tradeoracle-ai

# Install dependencies
pip install -r requirements.txt

# Configure API keys
cp .env.example .env
# Edit .env with your Google API key (required) and optionally MEXC/Telegram keys

# Launch
streamlit run app.py
```

## Tech Stack

| Component | Technology |
|-----------|-----------|
| AI Brain | Google Gemini 3 (gemini-2.5-flash) |
| Agent Framework | LangChain + Tool Calling |
| Market Data | MEXC Futures API (850+ contracts) |
| Technical Analysis | NumPy (RSI, MACD, ATR, Bollinger, Fibonacci) |
| Frontend | Streamlit |
| Database | SQLite (signal history) |
| Alerts | Telegram Bot API |

## Example Queries

- "Scan the market and find the top 5 breakout opportunities"
- "Analyze BTC/USDT with multi-timeframe analysis"
- "What's the current market regime?"
- "Show me the top gainers and losers today"
- "Check my position margin health"
- "Is ETH/USDT a good long entry right now?"

## License

MIT License - Built for the Gemini 3 Hackathon 2026
