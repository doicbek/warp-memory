---
name: warp-up
description: Review the current session and extract interesting problem-solving patterns, storing them as memories in Neo4j.
disable-model-invocation: true
allowed-tools: Read, Bash, Grep, Glob
---

# Warp-Up: Session Memory Extraction

You are reviewing the current Claude Code session to extract valuable problem-solving patterns and store them as structured memories in a Neo4j graph database. Future sessions will be able to query these memories via MCP.

## Locating the Plugin

Before running any commands, determine the warp-memory install location:

```bash
# Check for plugin install, fall back to legacy path
if [ -d "$HOME/.claude/plugins/cache/warp-memory" ]; then
  WARP_HOME="$HOME/.claude/plugins/cache/warp-memory"
elif [ -d "$HOME/.claude/warp-memory" ]; then
  WARP_HOME="$HOME/.claude/warp-memory"
else
  echo "ERROR: warp-memory not found" && exit 1
fi
echo "WARP_HOME=$WARP_HOME"
```

Use `$WARP_HOME` as a prefix for all `cli.py` invocations below.

## Step 1: Find the Session Transcript

The current session's transcript is a JSONL file. Find it:

```bash
# List recent transcripts for this project, sorted by modification time
ls -lt ~/.claude/projects/*/?.jsonl 2>/dev/null | head -5
```

Look for the most recently modified `.jsonl` file in `~/.claude/projects/`. The project directory name is derived from the working directory path with `/` replaced by `-`.

Read the transcript file. If it's very large, read it in chunks (e.g., first 500 lines, then next 500, etc.).

## Step 2: Query Existing Categories

Before categorizing memories, see what categories already exist:

```bash
python3 "$WARP_HOME/cli.py" categories
```

Use existing categories when they fit. Only create new ones when the pattern genuinely doesn't fit existing categories.

## Step 3: Analyze the Transcript

Look through the session for interesting patterns. Focus on:

1. **Error Recovery Workflows** - When something failed and was successfully recovered
   - Build failures diagnosed and fixed
   - Runtime errors traced to root cause
   - Configuration issues resolved

2. **Creative Problem-Solving** - Non-obvious approaches that worked
   - Workarounds for tool limitations
   - Clever use of available tools
   - Unconventional debugging strategies

3. **Tool Usage Patterns** - Effective tool combinations or usage
   - Which tools were used together effectively
   - Tool parameters that proved useful
   - Multi-step tool workflows

4. **Debugging Strategies** - Systematic debugging approaches
   - How errors were diagnosed
   - Which investigation steps led to the answer
   - Red herrings that were avoided or caught

5. **Architectural Decisions** - Design choices and their rationale
   - Why one approach was chosen over another
   - Trade-offs that were considered
   - Patterns that were applied

**Skip mundane patterns** like simple file reads, basic git operations, or straightforward edits that don't involve interesting problem-solving.

## Step 4: Extract Memories

For each interesting pattern found, create a structured memory. Produce output like:

```
### Memory 1: [Short descriptive title]

**Summary:** 2-3 sentences capturing the essence of the pattern. What was the problem? What was the approach? What was the outcome?

**Workflow:**
1. Step-by-step what was done
2. Include specific tools used at each step
3. Include key commands or search patterns
4. Note what worked and what didn't

**Tools Used:** [list of Claude Code tools, e.g., Grep, Edit, Bash, Read, Agent]

**Categories:** [hierarchical categories, e.g., "debugging", "debugging/import-errors"]
Use existing categories from Step 2 when they fit. Use kebab-case for new categories.
```

## Step 5: Store Each Memory

For each extracted memory, store it via the CLI:

```bash
python3 "$WARP_HOME/cli.py" store --json '{
  "title": "Fix Python import cycle by lazy-loading module",
  "summary": "When circular imports cause ImportError at runtime, the solution is to move the import inside the function that needs it. This avoids the cycle while keeping the dependency.",
  "workflow": "1. Identified circular import via ImportError traceback\n2. Used Grep to find all imports of the problematic module\n3. Identified the cycle: A imports B imports A\n4. Moved the import in module B inside the function that uses it\n5. Verified with Bash: python3 -c \"import A\" succeeded",
  "tools_used": ["Grep", "Edit", "Bash"],
  "categories": ["debugging", "debugging/import-errors"],
  "project": "/home/dbeck/myproject",
  "session_id": "abc-123"
}'
```

**Important:** Escape the JSON properly for shell. If the content contains single quotes, use a heredoc or escape them.

For complex JSON with special characters, write it to a temp file first:

```bash
cat > /tmp/warp_memory.json << 'JSONEOF'
{
  "title": "...",
  "summary": "...",
  ...
}
JSONEOF
python3 "$WARP_HOME/cli.py" store --json "$(cat /tmp/warp_memory.json)"
```

## Step 6: Report Results

After storing all memories, summarize what was captured:

- Number of memories stored
- Categories used (new and existing)
- Brief title of each memory

Format as a clean summary the user can review.

## Guidelines

- **Quality over quantity**: 2-3 excellent memories are better than 10 mediocre ones
- **Be specific**: Include actual error messages, file paths, and tool parameters when relevant
- **Think about retrieval**: Write titles and summaries that will match well when future sessions search for similar problems
- **Respect hierarchy**: Use parent/child categories (e.g., `debugging/neo4j-errors`) to keep the graph organized
- **Include the "why"**: Don't just describe what happened — capture why the approach worked
- **Session context**: Include the session_id and project path so memories can be traced back to their source
