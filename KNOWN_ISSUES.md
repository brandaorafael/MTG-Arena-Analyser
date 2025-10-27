# Known Issues

## Docker Log File Caching on macOS

### Issue
Docker on macOS caches mounted log files and does not automatically see new matches written to `Player.log` after the container starts. This is a known limitation of Docker's file system implementation on macOS.

### Symptoms
- Running `docker exec mtg-arena-parser ./get-cards-last-match.sh` shows an older match
- New matches don't appear until Docker is restarted

### Solutions

#### Option 1: Use the Wrapper Script (Recommended)
Use the provided wrapper script that automatically restarts Docker before parsing:

```bash
./run-parser.sh
```

This script:
1. Restarts the Docker container to clear the file cache
2. Waits for the container to be ready
3. Runs the parser with the latest log data

#### Option 2: Manual Restart
Restart Docker manually before each parse:

```bash
docker restart mtg-arena-parser
docker exec mtg-arena-parser ./get-cards-last-match.sh
```

#### Option 3: Run Locally Without Docker
If you have Python and PyYAML installed locally:

```bash
pip3 install  # One-time installation
./get-cards-last-match.sh
```

This avoids Docker entirely and always reads the latest log file.

### Why This Happens
Docker Desktop for Mac uses a virtual machine and file sharing layer (osxfs or VirtioFS) that caches file contents for performance. When MTG Arena writes to the log file, Docker's cache doesn't automatically invalidate, so the container continues reading the cached version until it's restarted.

### Future Improvements
Potential solutions being considered:
- Use a file watcher to detect log changes and trigger restarts
- Switch to polling the log file modification time
- Create a native macOS version that doesn't require Docker
