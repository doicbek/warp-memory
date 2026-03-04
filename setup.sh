#!/bin/bash
# Warp Memory - Neo4j startup and schema initialization

set -e

echo "=== Warp Memory Setup ==="

# Check if Neo4j is reachable
if python3 -c "
from neo4j import GraphDatabase
d = GraphDatabase.driver('bolt://localhost:7687', auth=('neo4j', 'password'))
d.verify_connectivity()
d.close()
print('connected')
" 2>/dev/null; then
    echo "Neo4j is reachable."
else
    echo "Neo4j is not reachable. Attempting to start..."
    # Try without sudo first (user-local config), then with sudo
    neo4j start 2>/dev/null || sudo neo4j start 2>/dev/null || {
        echo "ERROR: Could not start Neo4j. Please start it manually."
        exit 1
    }
    echo "Waiting for Neo4j to be ready..."
    for i in {1..30}; do
        if python3 -c "
from neo4j import GraphDatabase
d = GraphDatabase.driver('bolt://localhost:7687', auth=('neo4j', 'password'))
d.verify_connectivity()
d.close()
" 2>/dev/null; then
            echo "Neo4j is ready."
            break
        fi
        sleep 1
    done
fi

# Initialize schema
echo "Initializing schema..."
cd "$(dirname "$0")"
python3 cli.py schema

echo "=== Setup complete ==="
