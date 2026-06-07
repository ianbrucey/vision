"""
Vision — Database CLI for Agent SDK tools.

The agent calls these via Bash. Each subcommand wraps a database operation
and returns JSON to stdout. Stderr carries progress/diagnostic messages.

Usage:
    python3 -m backend.chat.cli list-cases [--status active] [--limit 20]
    python3 -m backend.chat.cli get-case --case-id 42
    python3 -m backend.chat.cli search-blocks --case-id 42 --query "adhesion"
    python3 -m backend.chat.cli get-document-structure --document-id 1
    python3 -m backend.chat.cli get-block-context --block-id 150 --window 3
    python3 -m backend.chat.cli get-strategies --case-id 42
    python3 -m backend.chat.cli get-strategy-tree --strategy-id 1
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

# Ensure the backend package is importable regardless of CWD
_BACKEND_DIR = Path(__file__).resolve().parent.parent  # backend/
sys.path.insert(0, str(_BACKEND_DIR))

from core.db import connect, ensure_schema


def _conn_factory():
    """Create a new database connection for each call."""
    ensure_schema()
    return connect()


def cmd_list_cases(args):
    from chat.tools import list_cases
    result = list_cases(_conn_factory, status=args.status, limit=args.limit)
    print(json.dumps(result, default=str, indent=2))


def cmd_get_case(args):
    from chat.tools import get_case
    result = get_case(_conn_factory, case_id=args.case_id)
    print(json.dumps(result, default=str, indent=2))


def cmd_search_blocks(args):
    from chat.tools import search_blocks
    result = search_blocks(
        _conn_factory,
        case_id=args.case_id,
        query=args.query,
        document_id=args.document_id,
        page_start=args.page_start,
        page_end=args.page_end,
        limit=args.limit,
    )
    print(json.dumps(result, default=str, indent=2))


def cmd_get_document_structure(args):
    from chat.tools import get_document_structure
    result = get_document_structure(_conn_factory, document_id=args.document_id)
    print(json.dumps(result, default=str, indent=2))


def cmd_get_block_context(args):
    from chat.tools import get_block_context
    result = get_block_context(
        _conn_factory, block_id=args.block_id, window=args.window
    )
    print(json.dumps(result, default=str, indent=2))


def cmd_get_strategies(args):
    from chat.tools import get_strategies
    result = get_strategies(_conn_factory, case_id=args.case_id)
    print(json.dumps(result, default=str, indent=2))


def cmd_get_strategy_tree(args):
    from chat.tools import get_strategy_tree
    result = get_strategy_tree(_conn_factory, strategy_id=args.strategy_id)
    print(json.dumps(result, default=str, indent=2))


def main():
    parser = argparse.ArgumentParser(description="Vision DB CLI")
    sub = parser.add_subparsers(dest="command")

    p = sub.add_parser("list-cases")
    p.add_argument("--status")
    p.add_argument("--limit", type=int, default=20)

    p = sub.add_parser("get-case")
    p.add_argument("--case-id", type=int, required=True)

    p = sub.add_parser("search-blocks")
    p.add_argument("--case-id", type=int, required=True)
    p.add_argument("--query", required=True)
    p.add_argument("--document-id", type=int)
    p.add_argument("--page-start", type=int)
    p.add_argument("--page-end", type=int)
    p.add_argument("--limit", type=int, default=20)

    p = sub.add_parser("get-document-structure")
    p.add_argument("--document-id", type=int, required=True)

    p = sub.add_parser("get-block-context")
    p.add_argument("--block-id", type=int, required=True)
    p.add_argument("--window", type=int, default=3)

    p = sub.add_parser("get-strategies")
    p.add_argument("--case-id", type=int, required=True)

    p = sub.add_parser("get-strategy-tree")
    p.add_argument("--strategy-id", type=int, required=True)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    commands = {
        "list-cases": cmd_list_cases,
        "get-case": cmd_get_case,
        "search-blocks": cmd_search_blocks,
        "get-document-structure": cmd_get_document_structure,
        "get-block-context": cmd_get_block_context,
        "get-strategies": cmd_get_strategies,
        "get-strategy-tree": cmd_get_strategy_tree,
    }
    commands[args.command](args)


if __name__ == "__main__":
    main()
