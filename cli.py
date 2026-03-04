#!/usr/bin/env python3
"""CLI interface for warp-up session memory system."""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import memory_store


def cmd_categories(args):
    """List existing category tree."""
    cats = memory_store.get_categories()
    if not cats:
        print(json.dumps({"categories": []}, indent=2))
        return

    # Build tree structure for display
    tree = {}
    for cat in cats:
        tree[cat["name"]] = cat

    print(json.dumps({"categories": cats}, indent=2))


def cmd_store(args):
    """Store a memory from JSON input."""
    data = json.loads(args.json)
    required = ["title", "summary", "workflow", "tools_used", "categories", "project", "session_id"]
    missing = [k for k in required if k not in data]
    if missing:
        print(json.dumps({"error": f"Missing fields: {missing}"}), file=sys.stderr)
        sys.exit(1)

    memory_id = memory_store.store_memory(
        title=data["title"],
        summary=data["summary"],
        workflow=data["workflow"],
        tools_used=data["tools_used"],
        categories=data["categories"],
        project=data["project"],
        session_id=data["session_id"],
    )
    print(json.dumps({"stored": True, "id": memory_id}))


def cmd_search(args):
    """Search memories by text query."""
    results = memory_store.search_memories(args.query, limit=args.limit)
    # Convert datetime objects to strings
    for r in results:
        for k, v in r.items():
            if hasattr(v, "isoformat"):
                r[k] = v.isoformat()
    print(json.dumps({"results": results}, indent=2))


def cmd_search_category(args):
    """Search memories by category."""
    results = memory_store.search_by_category(args.category, limit=args.limit)
    for r in results:
        for k, v in r.items():
            if hasattr(v, "isoformat"):
                r[k] = v.isoformat()
    print(json.dumps({"results": results}, indent=2))


def cmd_get(args):
    """Get full memory details."""
    result = memory_store.get_memory(args.id)
    if result is None:
        print(json.dumps({"error": "Memory not found"}), file=sys.stderr)
        sys.exit(1)
    for k, v in result.items():
        if hasattr(v, "isoformat"):
            result[k] = v.isoformat()
    print(json.dumps({"memory": result}, indent=2))


def cmd_transcript(args):
    """Read and return session transcript."""
    # Claude Code stores transcripts in project dirs
    project_dir = args.project_path.replace("/", "-").strip("-")
    transcript_dir = os.path.expanduser(f"~/.claude/projects/{project_dir}")

    # Find the transcript file matching session_id
    transcript_file = os.path.join(transcript_dir, f"{args.session_id}.jsonl")

    if not os.path.exists(transcript_file):
        # Try to find any matching file
        if os.path.isdir(transcript_dir):
            files = [f for f in os.listdir(transcript_dir) if f.endswith(".jsonl")]
            if files:
                # Return the most recent one if no specific session
                files.sort(key=lambda f: os.path.getmtime(os.path.join(transcript_dir, f)), reverse=True)
                transcript_file = os.path.join(transcript_dir, files[0])
            else:
                print(json.dumps({"error": f"No transcripts found in {transcript_dir}"}), file=sys.stderr)
                sys.exit(1)
        else:
            print(json.dumps({"error": f"Directory not found: {transcript_dir}"}), file=sys.stderr)
            sys.exit(1)

    # Read and return transcript
    entries = []
    with open(transcript_file, "r") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue

    print(json.dumps({
        "file": transcript_file,
        "entry_count": len(entries),
        "entries": entries,
    }))


def cmd_schema(args):
    """Initialize the database schema."""
    memory_store.ensure_schema()
    print(json.dumps({"schema": "initialized"}))


def main():
    parser = argparse.ArgumentParser(description="Warp Memory CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # categories
    subparsers.add_parser("categories", help="List category tree")

    # store
    store_p = subparsers.add_parser("store", help="Store a memory")
    store_p.add_argument("--json", required=True, help="JSON memory data")

    # search
    search_p = subparsers.add_parser("search", help="Search memories")
    search_p.add_argument("query", help="Search query")
    search_p.add_argument("--limit", type=int, default=5)

    # search-category
    cat_search_p = subparsers.add_parser("search-category", help="Browse by category")
    cat_search_p.add_argument("category", help="Category name")
    cat_search_p.add_argument("--limit", type=int, default=10)

    # get
    get_p = subparsers.add_parser("get", help="Get memory details")
    get_p.add_argument("id", help="Memory ID")

    # transcript
    trans_p = subparsers.add_parser("transcript", help="Read session transcript")
    trans_p.add_argument("session_id", help="Session ID")
    trans_p.add_argument("project_path", help="Project path")

    # schema
    subparsers.add_parser("schema", help="Initialize database schema")

    args = parser.parse_args()

    commands = {
        "categories": cmd_categories,
        "store": cmd_store,
        "search": cmd_search,
        "search-category": cmd_search_category,
        "get": cmd_get,
        "transcript": cmd_transcript,
        "schema": cmd_schema,
    }

    try:
        commands[args.command](args)
    except Exception as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        sys.exit(1)
    finally:
        memory_store.close()


if __name__ == "__main__":
    main()
