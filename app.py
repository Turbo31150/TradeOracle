"""
TradeOracle - Streamlit Application
Autonomous Crypto Trading Agent powered by Gemini 3
Hackathon Gemini 3 - February 2026
"""
import os
import sys
import time
import json
import streamlit as st
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))

from agent.gemini_agent import create_agent, run_query, ALL_TOOLS
from database.signals_db import save_decision, get_recent_signals, get_signal_stats
from config.settings import GOOGLE_API_KEY, GEMINI_MODEL

# Page config
st.set_page_config(
    page_title="TradeOracle - Gemini 3 Trading Agent",
    page_icon="https://raw.githubusercontent.com/google/generative-ai-docs/main/site/en/gemini-api/images/favicon.ico",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .stApp { background-color: #0e1117; }
    .main-title { font-size: 2.5em; font-weight: bold; color: #4FC3F7;
        text-align: center; margin-bottom: 0; }
    .sub-title { font-size: 1.1em; color: #90A4AE; text-align: center;
        margin-top: 0; margin-bottom: 30px; }
    .signal-long { background-color: #1b5e20; padding: 10px; border-radius: 8px;
        border-left: 4px solid #4caf50; margin: 5px 0; }
    .signal-short { background-color: #b71c1c; padding: 10px; border-radius: 8px;
        border-left: 4px solid #f44336; margin: 5px 0; }
    .signal-neutral { background-color: #37474f; padding: 10px; border-radius: 8px;
        border-left: 4px solid #78909c; margin: 5px 0; }
    .metric-card { background-color: #1a237e; padding: 15px; border-radius: 10px;
        text-align: center; margin: 5px; }
    .reasoning-box { background-color: #1a1a2e; border: 1px solid #4FC3F7;
        border-radius: 8px; padding: 15px; margin: 10px 0; }
    .tool-call { background-color: #263238; padding: 8px 12px; border-radius: 6px;
        margin: 3px 0; font-family: monospace; font-size: 0.85em; }
</style>
""", unsafe_allow_html=True)


def init_session():
    """Initialize session state"""
    if "agent" not in st.session_state:
        st.session_state.agent = None
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []


def create_agent_cached():
    """Create or return cached agent"""
    if st.session_state.agent is None:
        try:
            st.session_state.agent = create_agent(verbose=True)
        except Exception as e:
            st.error(f"Failed to create agent: {e}")
            return None
    return st.session_state.agent


def render_header():
    """Render the main header"""
    st.markdown('<p class="main-title">TradeOracle</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-title">Autonomous Crypto Trading Agent | Powered by Gemini 3 + Real-Time MEXC Data</p>', unsafe_allow_html=True)


def render_sidebar():
    """Render sidebar with controls"""
    with st.sidebar:
        st.markdown("### Agent Controls")

        # Quick actions
        st.markdown("**Quick Actions:**")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Scan Market", use_container_width=True):
                return "Scan the MEXC Futures market and find the top 5 trading opportunities right now. Show scores and reasons."
        with col2:
            if st.button("Top Movers", use_container_width=True):
                return "Show me the top 5 gainers and top 5 losers in the last 24h on MEXC Futures."

        col3, col4 = st.columns(2)
        with col3:
            if st.button("BTC Analysis", use_container_width=True):
                return "Perform a complete multi-timeframe analysis on BTC/USDT (15m, 1h, 4h). Should I go long, short, or wait?"
        with col4:
            if st.button("Market Regime", use_container_width=True):
                return "What is the current market regime? Check BTC for macro context."

        col5, col6 = st.columns(2)
        with col5:
            if st.button("Positions", use_container_width=True):
                return "Show me all my open positions on MEXC Futures with margin health status."
        with col6:
            if st.button("Margin Check", use_container_width=True):
                return "Check margin health of all my positions. Are any at risk?"

        st.markdown("---")

        # Agent info
        st.markdown("### Agent Info")
        st.markdown(f"**Model:** `{GEMINI_MODEL}`")
        st.markdown(f"**Tools:** {len(ALL_TOOLS)} available")
        st.markdown("**Capabilities:**")
        for t in ALL_TOOLS:
            st.markdown(f"- `{t.name}`")

        st.markdown("---")
        st.markdown("### About")
        st.markdown(
            "TradeOracle uses **Gemini 3** to autonomously analyze "
            "850+ crypto futures contracts, perform deep technical analysis, "
            "and generate trading signals with chain-of-thought reasoning."
        )
        st.markdown("Built for the **Gemini 3 Hackathon** (Feb 2026)")

    return None


def render_tool_calls(steps):
    """Render intermediate tool calls in a collapsible section"""
    if not steps:
        return

    with st.expander(f"Agent Reasoning ({len(steps)} tool calls)", expanded=False):
        for i, step in enumerate(steps):
            if isinstance(step, dict):
                tool_name = step.get('tool', 'unknown')
                tool_input = step.get('input', {})
                observation = step.get('output', '')

                st.markdown(f'<div class="tool-call">Step {i+1}: <b>{tool_name}</b></div>',
                            unsafe_allow_html=True)

                if isinstance(tool_input, dict):
                    for k, v in tool_input.items():
                        st.markdown(f"  `{k}`: {v}")
                elif isinstance(tool_input, str):
                    st.markdown(f"  Input: `{tool_input}`")

                obs_str = str(observation)
                if len(obs_str) > 500:
                    st.text(obs_str[:500] + "...")
                else:
                    st.text(obs_str)
                st.markdown("---")


def render_chat():
    """Render the chat interface"""
    # Display message history
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if "steps" in msg and msg["steps"]:
                render_tool_calls(msg["steps"])
            if "duration" in msg:
                st.caption(f"Response time: {msg['duration']:.1f}s")


def process_query(query: str):
    """Process a user query through the agent"""
    agent = create_agent_cached()
    if agent is None:
        st.error("Agent not initialized. Check your GOOGLE_API_KEY in .env")
        return

    # Add user message
    st.session_state.messages.append({"role": "user", "content": query})

    with st.chat_message("user"):
        st.markdown(query)

    # Process with agent
    with st.chat_message("assistant"):
        with st.spinner("TradeOracle is analyzing..."):
            start = time.time()
            result = run_query(agent, query, st.session_state.chat_history)
            duration = time.time() - start

        # Display response
        output = result["output"]
        steps = result.get("intermediate_steps", [])

        st.markdown(output)
        render_tool_calls(steps)
        st.caption(f"Response time: {duration:.1f}s | Tools used: {len(steps)}")

        # Save to history
        st.session_state.messages.append({
            "role": "assistant",
            "content": output,
            "steps": steps,
            "duration": duration,
        })

        # Update chat history for context
        st.session_state.chat_history.extend([
            {"role": "user", "content": query},
            {"role": "assistant", "content": output},
        ])
        # Keep last 10 exchanges
        if len(st.session_state.chat_history) > 20:
            st.session_state.chat_history = st.session_state.chat_history[-20:]

        # Save decision to DB
        try:
            tools_used = []
            for s in steps:
                if isinstance(s, dict):
                    tools_used.append(s.get('tool', 'unknown'))
            save_decision(
                query=query,
                response=output[:2000],
                tools_used=tools_used,
                model=GEMINI_MODEL,
                duration_ms=int(duration * 1000)
            )
        except Exception:
            pass


def main():
    init_session()
    render_header()

    # Check API key
    if not GOOGLE_API_KEY:
        st.error("GOOGLE_API_KEY not configured. Create a `.env` file from `.env.example` and add your Gemini API key.")
        st.code("cp .env.example .env\n# Edit .env and add your GOOGLE_API_KEY", language="bash")
        st.stop()

    # Sidebar actions
    sidebar_action = render_sidebar()

    # Main tabs
    tab1, tab2, tab3 = st.tabs(["Agent Chat", "Signal History", "Dashboard"])

    with tab1:
        render_chat()

        # Process sidebar action if any
        if sidebar_action:
            process_query(sidebar_action)
            st.rerun()

        # Chat input
        user_input = st.chat_input("Ask TradeOracle anything... (e.g., 'Analyze SOL/USDT' or 'Find breakout opportunities')")
        if user_input:
            process_query(user_input)
            st.rerun()

    with tab2:
        st.markdown("### Recent Signals")
        try:
            signals = get_recent_signals(limit=20)
            if signals:
                for s in signals:
                    css_class = f"signal-{s['direction'].lower()}" if s['direction'] in ['LONG', 'SHORT'] else 'signal-neutral'
                    st.markdown(
                        f'<div class="{css_class}">'
                        f'<b>{s["symbol"]}</b> | {s["direction"]} | Score: {s["score"]}/100 | '
                        f'${s["price"]:.6g} | {s["timestamp"]}</div>',
                        unsafe_allow_html=True
                    )
            else:
                st.info("No signals yet. Use the Agent Chat to generate trading signals.")
        except Exception as e:
            st.warning(f"Database not yet initialized: {e}")

    with tab3:
        st.markdown("### TradeOracle Dashboard")
        try:
            stats = get_signal_stats()
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Signals", stats.get('total', 0))
            with col2:
                st.metric("Long Signals", stats.get('long', 0))
            with col3:
                st.metric("Short Signals", stats.get('short', 0))
            with col4:
                st.metric("Avg Score", f"{stats.get('avg_score', 0):.0f}/100")

            if stats.get('top_symbols'):
                st.markdown("#### Most Analyzed Symbols")
                for s in stats['top_symbols']:
                    st.markdown(f"- **{s['symbol']}**: {s['count']} signals (avg score: {s['avg_score']:.0f})")
        except Exception:
            st.info("Dashboard will populate as you use the agent.")


if __name__ == "__main__":
    main()
