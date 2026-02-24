#!/usr/bin/env python3
"""CLI: Analyze a project for tokenization potential."""

import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.analyzer import analyze_project, generate_launch_report


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Analyze project")
    parser.add_argument("--title", required=True, help="Project title")
    parser.add_argument("--body", default="", help="Project description")
    parser.add_argument("--github", default="", help="GitHub URL")
    parser.add_argument("--json-file", default=None, help="Load project from JSON file")
    parser.add_argument("--report", action="store_true", help="Print human-readable report")
    args = parser.parse_args()

    if args.json_file:
        with open(args.json_file) as f:
            project = json.load(f)
    else:
        project = {
            "title": args.title,
            "body": args.body,
            "github_urls": [args.github] if args.github else [],
            "author": "cli",
        }

    analysis = analyze_project(project)

    if args.report:
        print(generate_launch_report(analysis))
    else:
        print(json.dumps(analysis, indent=2))


if __name__ == "__main__":
    main()
