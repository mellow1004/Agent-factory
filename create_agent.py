#!/usr/bin/env python3
"""
create_agent.py — CLI entry point for the Agent Factory.

Usage:
    python create_agent.py "SaaS Legal Expert"
    python create_agent.py "Cloud Architect" --model claude-sonnet-4-5-20250929
    python create_agent.py "DevOps Engineer" --output ./my_agents
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Ensure the package is importable when running from the project root
sys.path.insert(0, str(Path(__file__).parent))

from agent_factory.factory import create_agent, DEFAULT_MODEL


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a complete agent folder from a role description.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            '  python create_agent.py "SaaS Legal Expert"\n'
            '  python create_agent.py "Cloud Architect" --model claude-sonnet-4-5-20250929\n'
            '  python create_agent.py "DevOps Engineer" --output ./custom_agents\n'
        ),
    )
    parser.add_argument(
        "role",
        help='Role description, e.g. "SaaS Legal Expert" or a longer paragraph.',
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"Anthropic model to use (default: {DEFAULT_MODEL}).",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Directory to write agent folders into (default: agent_factory/agents/).",
    )
    parser.add_argument(
        "--api-key",
        default=None,
        help="Anthropic API key (default: reads ANTHROPIC_API_KEY env var).",
    )

    args = parser.parse_args()

    print(f"\n⚙️  Agent Factory")
    print(f"   Role:  {args.role}")
    print(f"   Model: {args.model}\n")

    try:
        result = create_agent(
            args.role,
            model=args.model,
            api_key=args.api_key,
            output_dir=args.output,
        )
    except Exception as exc:
        print(f"❌  Error: {exc}", file=sys.stderr)
        sys.exit(1)

    print(f"✅  Agent created: {result['display_name']}")
    print(f"   Folder: {result['agent_dir']}")
    print(f"   Files:  {', '.join(result['files_written'])}")
    print(f"\n   Run it:")
    print(f"   cd {result['agent_dir']} && python run_agent.py\n")


if __name__ == "__main__":
    main()
