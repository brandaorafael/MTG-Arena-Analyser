# MTG Arena Log Parser - Setup Guide

## Initial Setup

### 1. Configure Your Environment

Copy the example config file and update it with your paths:

```bash
cp config.yaml.example config.yaml
```

Edit `config.yaml` and update the paths to match your system:

```yaml
mtga:
  player_log: "/Users/YOUR_USERNAME/Library/Logs/Wizards Of The Coast/MTGA/Player.log"
  logs_dir: "/Users/YOUR_USERNAME/Library/Logs/Wizards Of The Coast/MTGA"
  card_database_dir: "/Users/YOUR_USERNAME/Library/Application Support/com.wizards.mtga/Downloads/Raw"
```

### 2. Generate Docker Environment File

Run the environment generator to create `.env` from your config:

```bash
python3 generate-env.py
```

Or if you don't have pyyaml installed locally, you can manually create `.env`:

```bash
cp config.yaml.example config.yaml
# Edit config.yaml with your paths
# Then manually create .env with:
MTGA_LOGS_DIR=/Your/Path/To/MTGA/Logs
MTGA_CARD_DB_DIR=/Your/Path/To/MTGA/Card/Database
```

### 3. Build and Run Docker Container

```bash
docker compose build
docker compose up -d
```

### 4. Run the Parser

```bash
docker exec mtg-arena-parser ./get-cards-last-match.sh
```

Or run directly (requires pyyaml to be installed):

```bash
./get-cards-last-match.sh
```

## Configuration Files

- `config.yaml` - Main configuration file (not in git, user-specific)
- `config.yaml.example` - Template for config.yaml
- `.env` - Docker environment variables (auto-generated, not in git)
- `generate-env.py` - Script to generate .env from config.yaml

## Updating Paths

If you need to change your MTG Arena installation paths:

1. Edit `config.yaml` with your new paths
2. Run `python3 generate-env.py` to update `.env`
3. Restart Docker: `docker compose down && docker compose up -d`
