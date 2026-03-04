"""Core Neo4j operations for warp-up session memory system."""

import logging
import uuid
from datetime import datetime, timezone

from neo4j import GraphDatabase

# Suppress neo4j driver warnings about non-existent labels/properties
logging.getLogger("neo4j").setLevel(logging.ERROR)

NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "password"

_driver = None


def get_driver():
    global _driver
    if _driver is None:
        _driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    return _driver


def close():
    global _driver
    if _driver:
        _driver.close()
        _driver = None


def ensure_schema():
    """Create indexes and constraints on first run."""
    driver = get_driver()
    with driver.session() as session:
        # Constraints
        session.run(
            "CREATE CONSTRAINT memory_id IF NOT EXISTS "
            "FOR (m:Memory) REQUIRE m.id IS UNIQUE"
        )
        session.run(
            "CREATE CONSTRAINT category_name IF NOT EXISTS "
            "FOR (c:Category) REQUIRE c.name IS UNIQUE"
        )
        session.run(
            "CREATE CONSTRAINT tool_name IF NOT EXISTS "
            "FOR (t:Tool) REQUIRE t.name IS UNIQUE"
        )
        # Full-text index for search
        try:
            session.run(
                "CREATE FULLTEXT INDEX memory_search IF NOT EXISTS "
                "FOR (m:Memory) ON EACH [m.title, m.summary, m.workflow]"
            )
        except Exception:
            pass  # Index may already exist
        # Regular indexes
        session.run(
            "CREATE INDEX memory_project IF NOT EXISTS "
            "FOR (m:Memory) ON (m.project)"
        )
        session.run(
            "CREATE INDEX memory_created IF NOT EXISTS "
            "FOR (m:Memory) ON (m.created_at)"
        )


def get_categories():
    """Return full category tree as nested dict."""
    driver = get_driver()
    with driver.session() as session:
        result = session.run(
            "MATCH (c:Category) "
            "OPTIONAL MATCH (parent:Category)-[:PARENT_OF]->(c) "
            "RETURN c.name AS name, c.display_name AS display_name, "
            "c.description AS description, c.level AS level, "
            "parent.name AS parent_name "
            "ORDER BY c.level, c.name"
        )
        categories = []
        for record in result:
            categories.append({
                "name": record["name"],
                "display_name": record["display_name"],
                "description": record["description"],
                "level": record["level"],
                "parent": record["parent_name"],
            })
        return categories


def _ensure_category(tx, name, display_name=None, description=None, parent_name=None):
    """Create a category if it doesn't exist, return it."""
    if display_name is None:
        display_name = name.replace("-", " ").title()
    level = 0
    if parent_name:
        # Get parent level
        parent = tx.run(
            "MATCH (p:Category {name: $name}) RETURN p.level AS level",
            name=parent_name,
        ).single()
        if parent:
            level = parent["level"] + 1

    tx.run(
        "MERGE (c:Category {name: $name}) "
        "ON CREATE SET c.display_name = $display_name, "
        "c.description = $description, c.level = $level",
        name=name,
        display_name=display_name,
        description=description or "",
        level=level,
    )

    if parent_name:
        tx.run(
            "MATCH (parent:Category {name: $parent}), (child:Category {name: $child}) "
            "MERGE (parent)-[:PARENT_OF]->(child)",
            parent=parent_name,
            child=name,
        )


def store_memory(title, summary, workflow, tools_used, categories, project, session_id):
    """Store a memory with categories and tool relationships.

    categories: list of category names. If a name contains '/',
    it's treated as a path (e.g. 'debugging/import-errors' creates
    both 'debugging' and 'import-errors' with parent relationship).
    """
    memory_id = str(uuid.uuid4())
    driver = get_driver()

    with driver.session() as session:
        def _store(tx):
            # Create Memory node
            tx.run(
                "CREATE (m:Memory {"
                "  id: $id, title: $title, summary: $summary,"
                "  workflow: $workflow, tools_used: $tools,"
                "  session_id: $session_id, project: $project,"
                "  created_at: datetime()"
                "})",
                id=memory_id,
                title=title,
                summary=summary,
                workflow=workflow,
                tools=tools_used,
                session_id=session_id,
                project=project,
            )

            # Process categories
            leaf_categories = set()
            for cat_path in categories:
                parts = cat_path.split("/")
                parent = None
                for part in parts:
                    _ensure_category(tx, part, parent_name=parent)
                    parent = part
                leaf_categories.add(parts[-1])

            # Link memory to leaf categories
            for cat_name in leaf_categories:
                tx.run(
                    "MATCH (m:Memory {id: $mid}), (c:Category {name: $cname}) "
                    "MERGE (m)-[:BELONGS_TO]->(c)",
                    mid=memory_id,
                    cname=cat_name,
                )

            # Link to Tool nodes
            for tool in tools_used:
                tx.run(
                    "MERGE (t:Tool {name: $name})",
                    name=tool,
                )
                tx.run(
                    "MATCH (m:Memory {id: $mid}), (t:Tool {name: $tname}) "
                    "MERGE (m)-[:USES_TOOL]->(t)",
                    mid=memory_id,
                    tname=tool,
                )

        session.execute_write(_store)

    return memory_id


def search_memories(query, limit=5):
    """Full-text search on title, summary, and workflow."""
    driver = get_driver()
    with driver.session() as session:
        # Escape special Lucene characters and add fuzzy matching
        escaped = query.replace('"', '\\"')
        result = session.run(
            "CALL db.index.fulltext.queryNodes('memory_search', $search_text) "
            "YIELD node, score "
            "RETURN node.id AS id, node.title AS title, "
            "node.summary AS summary, node.tools_used AS tools_used, "
            "node.project AS project, node.created_at AS created_at, "
            "score "
            "ORDER BY score DESC LIMIT $limit",
            search_text=escaped,
            limit=limit,
        )
        return [dict(record) for record in result]


def search_by_category(category_name, limit=10):
    """Get memories belonging to a category (including child categories)."""
    driver = get_driver()
    with driver.session() as session:
        result = session.run(
            "MATCH (root:Category {name: $name})-[:PARENT_OF*0..]->(cat:Category) "
            "WITH DISTINCT cat "
            "MATCH (m:Memory)-[:BELONGS_TO]->(cat) "
            "RETURN DISTINCT m.id AS id, m.title AS title, "
            "m.summary AS summary, m.tools_used AS tools_used, "
            "m.project AS project, m.created_at AS created_at "
            "ORDER BY m.created_at DESC LIMIT $limit",
            name=category_name,
            limit=limit,
        )
        return [dict(record) for record in result]


def get_memory(memory_id):
    """Get full memory details including categories and tools."""
    driver = get_driver()
    with driver.session() as session:
        result = session.run(
            "MATCH (m:Memory {id: $id}) "
            "OPTIONAL MATCH (m)-[:BELONGS_TO]->(c:Category) "
            "OPTIONAL MATCH (m)-[:USES_TOOL]->(t:Tool) "
            "RETURN m.id AS id, m.title AS title, m.summary AS summary, "
            "m.workflow AS workflow, m.tools_used AS tools_used, "
            "m.session_id AS session_id, m.project AS project, "
            "m.created_at AS created_at, "
            "collect(DISTINCT c.name) AS categories, "
            "collect(DISTINCT t.name) AS tools",
            id=memory_id,
        ).single()
        if result is None:
            return None
        return dict(result)
