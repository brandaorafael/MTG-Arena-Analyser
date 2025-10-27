#!/bin/bash

# MTG Arena Log Parser
# Interactive mode: lists all matches and lets user select one

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_CMD=python3

MATCH_PARSER="$SCRIPT_DIR/src/app.py"

# Call interactive Python parser
if [ -f "$MATCH_PARSER" ]; then
    $PYTHON_CMD "$MATCH_PARSER" interactive
else
    echo "ERROR: Parser not found: $MATCH_PARSER"
    exit 1
fi
