"""
TradeOracle - Gemini 3 Agent (Hardened)
LangChain Agent powered by Gemini with Function Calling + Thinking
The brain of the autonomous trading oracle.
Features: Smart Retry with exponential backoff for API rate limits.
"""
import os
import time
from typing import Optional, Dict, Any, List
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
from langchain_core.output_parsers import StrOutputParser

from config.settings import GOOGLE_API_KEY, GEMINI_MODEL, GEMINI_THINKING_MODEL
from tools.market_scanner import scan_market, get_coin_price, get_top_movers, get_ohlcv_data
from tools.technical_analysis import analyze_coin_technical, get_market_regime, multi_timeframe_analysis
from tools.portfolio import get_positions, check_margin_health
from tools.alerts import send_telegram_alert

# System prompt - The Trading Oracle's personality and reasoning framework
SYSTEM_PROMPT = """You are TradeOracle, an elite autonomous crypto trading agent powered by Gemini 3.

YOUR CAPABILITIES:
- Scan 850+ MEXC Futures contracts in real-time
- Deep technical analysis (RSI, MACD, ATR, Bollinger, Fibonacci, patterns)
- Multi-timeframe trend alignment (15m, 1h, 4h)
- Market regime detection (trending, ranging, volatile, breakout)
- Portfolio monitoring with margin health tracking
- Telegram alerts for critical signals

REASONING PROTOCOL (Chain of Thought):
For every trading question, you MUST follow this exact process:

1. CONTEXT: What is the current market regime? Check BTC first for macro context.
2. DATA COLLECTION: Use your tools to gather real data. NEVER guess prices or indicators.
3. TECHNICAL ANALYSIS: Cross-reference multiple indicators (RSI + MACD + EMA + Volume).
4. RISK ASSESSMENT: What's the risk/reward? Where are the key levels?
5. DECISION: BUY, SELL, or WAIT - with specific entry, TP, and SL levels.
6. CONFIDENCE: Rate your confidence 1-10 and explain why.

TRADING RULES:
- Always check at least 2 timeframes before recommending a trade
- Never recommend a trade without checking RSI (avoid >70 for longs, <30 for shorts)
- Volume must confirm the signal (above average = stronger)
- Bollinger squeeze = potential explosive move, be ready
- EMA alignment across timeframes = highest confidence signals
- When uncertain, recommend WAIT. Preserving capital is a valid strategy.

COMMUNICATION STYLE:
- Be precise with numbers (prices, percentages, levels)
- Show your reasoning step by step
- Flag risks explicitly
- Use clear signal format: SYMBOL | DIRECTION | ENTRY | TP1/TP2/TP3 | SL | CONFIDENCE
"""

# All available tools
ALL_TOOLS = [
    scan_market,
    get_coin_price,
    get_top_movers,
    get_ohlcv_data,
    analyze_coin_technical,
    get_market_regime,
    multi_timeframe_analysis,
    get_positions,
    check_margin_health,
    send_telegram_alert,
]


class TradeOracleAgent:
    """Autonomous Trading Agent using Gemini 3 with tool calling."""

    def __init__(self, model_name: Optional[str] = None, temperature: float = 0.1):
        if not GOOGLE_API_KEY:
            raise ValueError("GOOGLE_API_KEY not set.")

        self.llm = ChatGoogleGenerativeAI(
            model=model_name or GEMINI_MODEL,
            temperature=temperature,
            google_api_key=GOOGLE_API_KEY,
        )
        self.llm_with_tools = self.llm.bind_tools(ALL_TOOLS)
        self.tools_map = {t.name: t for t in ALL_TOOLS}
        self.max_iterations = 10

    @staticmethod
    def _extract_text(content) -> str:
        """Extract text from Gemini response content (handles str or list of blocks)."""
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts = []
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    parts.append(block["text"])
                elif isinstance(block, str):
                    parts.append(block)
            return "\n".join(parts) if parts else ""
        return str(content) if content else ""

    def _invoke_with_retry(self, messages, max_retries: int = 3):
        """Invoke LLM with smart retry for 429/503 errors."""
        for attempt in range(max_retries):
            try:
                return self.llm_with_tools.invoke(messages)
            except Exception as e:
                err = str(e)
                if ("429" in err or "503" in err or "quota" in err.lower()
                        or "resource" in err.lower()):
                    wait = [2, 5, 10][min(attempt, 2)]
                    time.sleep(wait)
                    if attempt == max_retries - 1:
                        raise
                else:
                    raise

    def invoke(self, query: str, chat_history: List = None) -> Dict[str, Any]:
        """Run a query through the agent with autonomous tool calling."""
        messages = [SystemMessage(content=SYSTEM_PROMPT)]

        if chat_history:
            for msg in chat_history[-10:]:
                if msg.get("role") == "user":
                    messages.append(HumanMessage(content=msg["content"]))
                elif msg.get("role") == "assistant":
                    messages.append(AIMessage(content=msg["content"]))

        messages.append(HumanMessage(content=query))

        intermediate_steps = []

        for iteration in range(self.max_iterations):
            response = self._invoke_with_retry(messages)
            messages.append(response)

            # Check if the model wants to call tools
            if not response.tool_calls:
                # No more tool calls - return final response
                return {
                    "output": self._extract_text(response.content) or "Analysis complete.",
                    "intermediate_steps": intermediate_steps,
                    "success": True,
                    "iterations": iteration + 1,
                }

            # Execute each tool call
            for tool_call in response.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]
                tool_id = tool_call.get("id", f"call_{iteration}")

                if tool_name in self.tools_map:
                    try:
                        tool_result = self.tools_map[tool_name].invoke(tool_args)
                    except Exception as e:
                        tool_result = f"Tool error: {str(e)}"
                else:
                    tool_result = f"Unknown tool: {tool_name}"

                # Record step
                intermediate_steps.append({
                    "tool": tool_name,
                    "input": tool_args,
                    "output": str(tool_result)[:1000],
                })

                # Add tool response to messages
                messages.append(ToolMessage(
                    content=str(tool_result),
                    tool_call_id=tool_id,
                ))

        # Max iterations reached
        return {
            "output": "Maximum analysis depth reached. " + self._extract_text(response.content),
            "intermediate_steps": intermediate_steps,
            "success": True,
            "iterations": self.max_iterations,
        }


def create_agent(model_name: Optional[str] = None, temperature: float = 0.1, verbose: bool = True):
    """Create the TradeOracle agent."""
    return TradeOracleAgent(model_name=model_name, temperature=temperature)


def run_query(agent, query: str, chat_history: list = None) -> Dict[str, Any]:
    """Run a query through the TradeOracle agent."""
    try:
        return agent.invoke(query, chat_history)
    except Exception as e:
        return {
            "output": f"Agent error: {str(e)}",
            "intermediate_steps": [],
            "success": False,
        }
