#!/usr/bin/env python3
"""CLI: Run the full SurgeScout pipeline (Scout → Analyze → Report)."""

import json
import sys
import os
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s", datefmt="%H:%M:%S")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="SurgeScout Full Pipeline")
    parser.add_argument("--submolts", nargs="+", default=["lablab", "cryptocurrency", "defi", "agents"])
    parser.add_argument("--min-score", type=int, default=30)
    parser.add_argument("--output", default=None, help="Save results to file")
    args = parser.parse_args()

    from src.moltbook import scout_moltbook
    from src.analyzer import analyze_batch, generate_launch_report

    # 1. Scout
    print("\n=== PHASE 1: SCOUTING ===")
    projects = scout_moltbook(submolts=args.submolts)
    print(f"Found {len(projects)} project candidates\n")

    if not projects:
        print("No projects found. Try different submolts or keywords.")
        return

    # 2. Analyze
    print("=== PHASE 2: ANALYZING ===")
    analyses = analyze_batch(projects[:5], min_score=args.min_score)
    print(f"Analyzed {len(analyses)} projects above threshold {args.min_score}\n")

    # 3. Report
    print("=== PHASE 3: REPORTS ===\n")
    for i, analysis in enumerate(analyses[:3]):
        report = generate_launch_report(analysis)
        print(report)
        print("\n" + "=" * 60 + "\n")

    # Save
    if args.output:
        results = {
            "scouted": len(projects),
            "analyzed": len(analyses),
            "analyses": analyses,
        }
        with open(args.output, "w") as f:
            json.dump(results, f, indent=2)
        print(f"Results saved to {args.output}")


if __name__ == "__main__":
    main()
