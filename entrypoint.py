"""
TradeOracle - Dual Mode Entrypoint
  --mode standalone  : Streamlit UI (default)
  --mode mcp         : MCP Server (stdio or sse)
  --mode pipeline    : Run Domino Pipeline once (CLI)
"""
import argparse
import json
import os
import sys


def main():
    parser = argparse.ArgumentParser(description="TradeOracle - Trading AI Platform")
    parser.add_argument("--mode", choices=["standalone", "mcp", "pipeline"],
                        default="standalone",
                        help="Run mode: standalone (Streamlit), mcp (MCP server), pipeline (single run)")
    parser.add_argument("--transport", choices=["stdio", "sse"], default="stdio",
                        help="MCP transport mode (stdio or sse)")
    parser.add_argument("--port", type=int, default=8000,
                        help="Port for SSE transport")
    parser.add_argument("--min-score", type=int, default=70,
                        help="Pipeline: minimum scan score")
    parser.add_argument("--top-n", type=int, default=5,
                        help="Pipeline: max symbols to analyze")
    parser.add_argument("--alert-threshold", type=int, default=75,
                        help="Pipeline: min confidence for Telegram alert")
    args = parser.parse_args()

    if args.mode == "standalone":
        os.system("streamlit run app.py --server.headless true")

    elif args.mode == "mcp":
        from mcp_server.server import mcp
        if args.transport == "sse":
            mcp.run(transport="sse", port=args.port)
        else:
            mcp.run(transport="stdio")

    elif args.mode == "pipeline":
        from pipeline.domino import run_domino
        print("Running Domino Pipeline...\n")
        result = run_domino(
            min_score=args.min_score,
            top_n=args.top_n,
            alert_threshold=args.alert_threshold,
        )
        print(json.dumps(result, indent=2, default=str))

        if result.get("signals"):
            print(f"\n{len(result['signals'])} signal(s) found!")
        else:
            print("\nNo signals promoted.")
        print(f"Duration: {result.get('duration_ms', 0)}ms")


if __name__ == "__main__":
    main()
