#!/bin/bash

# Docker wrapper script for MTG Arena match parser
# Restarts the Docker container to refresh the log file cache (macOS requirement)
# Then runs the parser in interactive mode

echo "Restarting Docker container to refresh log file cache..."
docker restart mtg-arena-parser > /dev/null 2>&1

# Wait for container to be ready
sleep 2

# Run the parser in interactive mode
docker exec -i mtg-arena-parser ./parse-interactive.sh
