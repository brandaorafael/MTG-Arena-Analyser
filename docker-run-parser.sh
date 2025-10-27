#!/bin/bash

# Docker wrapper script to parse the latest MTG Arena match
# Restarts the Docker container to refresh the log file cache (macOS requirement)

echo "🔄 Restarting Docker container to refresh log file cache..."
docker restart mtg-arena-parser > /dev/null 2>&1

# Wait for container to be ready
sleep 2

# Run the parser
docker exec mtg-arena-parser ./get-cards-last-match.sh
