#!/bin/bash

# MTG Arena Log Parser
# Extracts opponent's cards from the most recent match

PLAYER_LOG="/Users/rafael.brandao/Library/Logs/Wizards Of The Coast/MTGA/Player.log"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "🔍 MTG Arena Match Log Parser"
echo "================================"
echo ""

# Check if log file exists
if [ ! -f "$PLAYER_LOG" ]; then
    echo "❌ Player.log not found at: $PLAYER_LOG"
    echo "Please make sure MTG Arena has been run at least once."
    exit 1
fi

# Find the most recent match ID
echo "🎮 Finding most recent match..."
LAST_MATCH=$(grep -o 'matchId [a-f0-9-]\{36\}' "$PLAYER_LOG" | tail -1 | awk '{print $2}')

if [ -z "$LAST_MATCH" ]; then
    echo "❌ No matches found in log file"
    exit 1
fi

echo "Match ID: $LAST_MATCH"
echo ""

# Call enhanced Python parser
if [ -f "$SCRIPT_DIR/parse_cards_enhanced.py" ]; then
    python3 "$SCRIPT_DIR/parse_cards_enhanced.py" "$PLAYER_LOG" "$LAST_MATCH"
else
    echo "❌ Parser not found: $SCRIPT_DIR/parse_cards_enhanced.py"
    exit 1
fi
