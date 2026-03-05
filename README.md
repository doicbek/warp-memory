# warp-memory

Session memory system for Claude Code. Captures problem-solving patterns, debugging strategies, and tool usage workflows from session transcripts and stores them in a Neo4j graph database. Future sessions query relevant memories via an MCP server.

## Architecture

```
/warp-up skill (SKILL.md)
  │  Reads session JSONL transcript, extracts patterns
  │
  ▼  Bash(python3 cli.py ...)
Python Backend (memory_store.py + cli.py)
  │  Neo4j driver for graph operations
  │
  ▼
Neo4j Graph Database
  (:Category)-[:PARENT_OF]->(:Category)
  (:Memory)-[:BELONGS_TO]->(:Category)
  (:Memory)-[:USES_TOOL]->(:Tool)
  ▲
  │
MCP Server (mcp_server.py)
  Available to all sessions + sub-agents
```

## Setup

### Prerequisites

- Python 3 with `neo4j` and `mcp` packages
- Neo4j running on `bolt://localhost:7687` (auth: `neo4j`/`password`)

```bash
pip install neo4j mcp
```

### Install as Claude Code Plugin

```bash
# Install directly from GitHub
claude plugin add --url https://github.com/doicbek/warp-memory

# Or install from a local clone
git clone git@github.com:doicbek/warp-memory.git ~/.claude/warp-memory
claude --plugin-dir ~/.claude/warp-memory
```

This registers the MCP server and the `/warp-up` skill automatically.

### Start Neo4j

```bash
# Start Neo4j and initialize schema
bash ~/.claude/warp-memory/setup.sh
```

### Legacy Install (manual)

If you prefer to set things up manually without the plugin system:

```bash
# Clone into Claude Code config directory
git clone git@github.com:doicbek/warp-memory.git ~/.claude/warp-memory

# Register MCP server (user scope, available to all projects)
claude mcp add --transport stdio --scope user warp-memory -- python3 ~/.claude/warp-memory/mcp_server.py

# Install the warp-up skill
mkdir -p ~/.claude/skills/warp-up
cp ~/.claude/warp-memory/skills/warp-up/SKILL.md ~/.claude/skills/warp-up/SKILL.md
```

## Usage

### CLI

```bash
# Initialize database schema
python3 cli.py schema

# List category tree
python3 cli.py categories

# Store a memory
python3 cli.py store --json '{
  "title": "Fix circular import by lazy-loading",
  "summary": "Moved import inside function to break cycle.",
  "workflow": "1. Identified cycle via traceback\n2. Moved import into function body",
  "tools_used": ["Grep", "Edit"],
  "categories": ["debugging", "debugging/import-errors"],
  "project": "/home/user/myproject",
  "session_id": "abc-123"
}'

# Search memories
python3 cli.py search "import error"

# Browse by category
python3 cli.py search-category "debugging"

# Get full memory details
python3 cli.py get <memory-id>
```

### MCP Tools (available in Claude Code sessions)

| Tool | Description |
|------|-------------|
| `search_memories` | Full-text search across titles, summaries, and workflows |
| `browse_categories` | Return the full category tree |
| `get_memory` | Get complete details for a memory by ID |
| `get_memories_for_task` | Find memories relevant to a task description (returns full workflows) |
| `search_by_category` | Browse memories within a category and its children |

### Warp-Up Skill

Run `/warp-up` at the end of a Claude Code session to extract and store interesting patterns from the session transcript. The skill:

1. Finds the current session's JSONL transcript
2. Queries existing categories for graph-aware categorization
3. Identifies error recovery workflows, debugging strategies, creative solutions, and effective tool usage
4. Stores structured memories with hierarchical categories

## Graph Schema

```
(:Memory {id, title, summary, workflow, tools_used, session_id, project, created_at})
(:Category {name, display_name, description, level})
(:Tool {name})

(:Memory)-[:BELONGS_TO]->(:Category)
(:Category)-[:PARENT_OF]->(:Category)
(:Memory)-[:USES_TOOL]->(:Tool)
```

Categories are hierarchical and self-organizing. Passing `["debugging", "debugging/import-errors"]` creates both categories with a `PARENT_OF` relationship.

## Configuration

Neo4j connection defaults in `memory_store.py`:

```python
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "password"
```

## License

MIT
