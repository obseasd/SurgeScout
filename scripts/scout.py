#!/usr/bin/env python3
"""CLI: Scout Moltbook for promising projects."""

import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.moltbook import scout_moltbook


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Scout Moltbook")
    parser.add_argument("--submolts", nargs="+", default=None)
    parser.add_argument("--keywords", nargs="+", default=None)
    parser.add_argument("--output", default=None, help="Save results to file")
    args = parser.parse_args()

    projects = scout_moltbook(submolts=args.submolts, keywords=args.keywords)

    if args.output:
        with open(args.output, "w") as f:
            json.dump(projects, f, indent=2)
        print(f"Saved {len(projects)} projects to {args.output}")
    else:
        print(json.dumps(projects, indent=2))

    print(f"\nTotal: {len(projects)} project candidates found")


if __name__ == "__main__":
    main()
