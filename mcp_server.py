#!/usr/bin/env python3
"""MCP server for warp-up session memory system.

Provides tools for searching and browsing memories stored in Neo4j.
Registered in ~/.claude/settings.json for use by all sessions and sub-agents.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mcp.server.fastmcp import FastMCP
import memory_store

mcp = FastMCP("warp-memory")


@mcp.tool()
def search_memories(query: str, limit: int = 5) -> dict:
    """Search session memories by text query.

    Searches across memory titles, summaries, and workflows using full-text search.
    Use this to find relevant past problem-solving patterns, debugging strategies,
    or tool usage examples.

    Args:
        query: Search text (e.g., "import error", "neo4j connection", "git rebase")
        limit: Maximum number of results to return (default 5)
    """
    results = memory_store.search_memories(query, limit=limit)
    for r in results:
        for k, v in r.items():
            if hasattr(v, "isoformat"):
                r[k] = v.isoformat()
    return {"results": results, "count": len(results)}


@mcp.tool()
def browse_categories() -> dict:
    """Get the full category tree of stored memories.

    Returns all categories organized hierarchically. Use this to understand
    what kinds of memories are available before searching.
    """
    categories = memory_store.get_categories()
    return {"categories": categories}


@mcp.tool()
def get_memory(id: str) -> dict:
    """Get full details of a specific memory by ID.

    Returns the complete memory including title, summary, step-by-step workflow,
    tools used, categories, and source session info.

    Args:
        id: The UUID of the memory to retrieve
    """
    result = memory_store.get_memory(id)
    if result is None:
        return {"error": "Memory not found"}
    for k, v in result.items():
        if hasattr(v, "isoformat"):
            result[k] = v.isoformat()
    return {"memory": result}


@mcp.tool()
def get_memories_for_task(task_description: str, limit: int = 5) -> dict:
    """Find memories relevant to a specific task you're about to work on.

    Optimized for agent task context - searches for memories that might help
    with the described task. Returns memories with their full workflows so
    you can follow proven patterns.

    Args:
        task_description: Description of the task (e.g., "fix circular import in Python project")
        limit: Maximum number of results (default 5)
    """
    results = memory_store.search_memories(task_description, limit=limit)
    # Enrich with full details for the top results
    enriched = []
    for r in results[:limit]:
        full = memory_store.get_memory(r["id"])
        if full:
            for k, v in full.items():
                if hasattr(v, "isoformat"):
                    full[k] = v.isoformat()
            enriched.append(full)
    return {"memories": enriched, "count": len(enriched)}


@mcp.tool()
def search_by_category(category: str, limit: int = 10) -> dict:
    """Browse memories in a specific category.

    Returns memories belonging to the given category and its children.
    Use browse_categories() first to see available categories.

    Args:
        category: Category name in kebab-case (e.g., "debugging", "error-recovery")
        limit: Maximum number of results (default 10)
    """
    results = memory_store.search_by_category(category, limit=limit)
    for r in results:
        for k, v in r.items():
            if hasattr(v, "isoformat"):
                r[k] = v.isoformat()
    return {"results": results, "count": len(results)}


if __name__ == "__main__":
    mcp.run(transport="stdio")
