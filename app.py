#!/usr/bin/env python3
"""SurgeScout — AI Deal Flow Agent for Internet Capital Markets.

Usage:
    python app.py                # Start on http://localhost:8899
    python app.py --port 3000    # Custom port
"""

import argparse
import logging
import os
import sys

# Ensure src is importable
sys.path.insert(0, os.path.dirname(__file__))


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    parser = argparse.ArgumentParser(description="SurgeScout")
    parser.add_argument("--port", type=int, default=None)
    parser.add_argument("--host", default=None)
    args = parser.parse_args()

    # Import after path setup
    from src import config
    from src.server import app

    port = int(os.getenv("PORT", 0)) or args.port or config.PORT
    host = args.host or config.HOST

    has_key = bool(config.ANTHROPIC_API_KEY or config.OPENAI_API_KEY)

    print()
    print("  SURGESCOUT — AI Deal Flow Agent")
    print(f"  http://{host}:{port}")
    print(f"  AI Provider: {config.AI_PROVIDER}")
    print(f"  API Key: {'configured' if has_key else 'MISSING'}")
    print()

    import uvicorn
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
