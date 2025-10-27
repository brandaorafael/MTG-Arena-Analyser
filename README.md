# MTG Arena Log Parser

Custom-built tools to extract and analyze MTG Arena match data from detailed logs.

## Features

- Interactive arrow-key navigation for browsing matches
- Shows your revealed cards and opponent's revealed cards
- Tracks cards across all zones (hand, battlefield, graveyard, exile)
- Displays deck statistics (revealed vs unrevealed breakdown)
- Shows opponent's name and match timestamps

## Quick Start

### Step 1: Configure and Build

See [SETUP.md](SETUP.md) for detailed setup instructions including:
- Creating your `config.yaml`
- Building the Docker container
- Running the parser

### Step 2: Enable Detailed Logging

**IMPORTANT:** You must enable detailed logging in MTG Arena:

1. Launch MTG Arena
2. Click the gear icon in the top right
3. Go to **View Account** (bottom of settings menu)
4. Enable **Detailed Logs (Plugin Support)**
5. Restart MTG Arena

Without detailed logging, the parser cannot extract card information.

### Step 3: Play a Match

Play a match in MTG Arena with detailed logging enabled.

### Step 4: Analyze Matches

```bash
./docker-parse-interactive.sh
```

This will:
1. List all matches found in your log file
2. Use arrow keys (↑/↓) to navigate between matches
3. Press Enter to view match details
4. Press Enter again to return to the menu
5. Press 'q' or Esc to quit

The interface remembers your last position, so you can quickly browse multiple matches.

> **Note:** On macOS, Docker caches log files. The wrapper script handles this automatically by restarting the container. See [KNOWN_ISSUES.md](KNOWN_ISSUES.md) for details.

## What the Parser Shows

### Your Deck
- All cards you've revealed (in hand or played)
- Cards grouped by type (Creatures, Instants, Sorceries, etc.)
- Full deck size and revealed/unrevealed breakdown

### Opponent's Deck
- Opponent's name
- All cards opponent has revealed
- Cards grouped by type
- Total unique cards and total revealed cards count

### Example Output

```
MTG Arena Match Log Parser

Use arrow keys to navigate, Enter to select, q to quit

======================================================================
  #    Start Time           End Time             Opponent
======================================================================
  1    2025-10-27 01:23:29  2025-10-27 01:27:15  Verity
> 2    2025-10-27 01:27:40  2025-10-27 01:34:52  Empadao

[Press Enter to view match]

Selected match vs Empadao
Match ID: 0fee9a7e-87df-4fa7-bed1-e2d8f639a36e

Parsing detailed logs for match: 0fee9a7e...
You are seat 1

============================================================
YOUR DECK
============================================================

REVEALED CARDS:

  Creatures (7):
    • Ajani's Pridemate
    • Essence Channeler (x2)
    • Hinterland Sanctifier
    • Thunderbond Vanguard
    • Voice of Victory (x2)

  Sorceries (1):
    • Swiftspear's Teachings

  Enchantments (1):
    • Waystone's Guidance

  Lands (6):
    • Clifftop Retreat
    • Plains (x3)
    • Starting Town
    • Wind-Scarred Crag

Deck: 60 cards total | 15 revealed | 45 unrevealed

============================================================
OPPONENT'S DECK (Empadao)
============================================================

REVEALED CARDS:

  Creatures (4):
    • Ajani's Pridemate
    • Exemplar of Light
    • Leonin Vanguard
    • Sun-Blessed Healer

  Sorceries (1):
    • Exorcise

  Enchantments (2):
    • Authority of the Consuls (x2)

  Lands (4):
    • Plains (x4)

Revealed: 7 unique cards | 11 total cards

============================================================
```

## Advanced Usage

### Interactive Mode (Default)

List all matches and select one interactively:

```bash
# With Docker
./docker-parse-interactive.sh

# Without Docker
./parse-interactive.sh
```

### Parse a Specific Match Directly

If you know the match ID:

```bash
# With Docker
docker exec mtg-arena-parser python3 src/app.py parse-match <log-file> <match-id>

# Without Docker
python3 src/app.py parse-match <log-file> <match-id>
```

## File Locations

### MTGA Logs and Data

**Player Log** (main log file parsed):
```
~/Library/Logs/Wizards Of The Coast/MTGA/Player.log
```

**Card Database** (SQLite database with 21,477 cards):
```
~/Library/Application Support/com.wizards.mtga/Downloads/Raw/Raw_CardDatabase_*.mtga
```

**Match History** (optional):
```
~/Library/Application Support/com.wizards.mtga/Logs/Logs/UTC_Log - *.log
```

### Project Files

**Card Database JSON** (extracted from SQLite):
```
./src/cards_database/card_database.json
```

**Configuration**:
```
./config.yaml
```

## How It Works

### Parsing Process

1. **Seat Detection**: Uses `GREMessageType_ConnectResp` to identify the local player's seat
2. **Instance Tracking**: Tracks all card instances and their grpId mappings
3. **Location Tracking**: Monitors cards as they move between zones
4. **Zone Parsing**: Uses explicit zone lists for authoritative hand contents
5. **Card Counting**: Only counts cards in their final location, filtering out mulligan artifacts

### Zone IDs

| Zone | Name | Visibility |
|------|------|------------|
| 28 | Battlefield | Public |
| 29 | Exile | Public |
| 31 | Seat 1's hand | Private to Seat 1 |
| 33 | Seat 1's graveyard | Public |
| 35 | Seat 2's hand | Private to Seat 2 |
| 37 | Seat 2's graveyard | Public |

### Card Database

The parser uses MTGA's SQLite database located at:
```
~/Library/Application Support/com.wizards.mtga/Downloads/Raw/Raw_CardDatabase_*.mtga
```

The database contains:
- `Cards` table with grpId, rarity, types, etc.
- `Localizations_enUS` table with card names
- `Abilities` and `Enums` tables for game mechanics

## Important Notes

### Requirements

- **Detailed logging MUST be enabled** in MTG Arena (Settings → View Account → Detailed Logs)
- Without detailed logging, the parser cannot extract card information

### Privacy

- All parsing is done locally on your machine
- No data is sent to external servers
- Card database is extracted from your local MTGA installation

### Limitations

- Only tracks revealed cards (played, discarded, or in hand)
- Cannot see opponent's unrevealed cards in library
- Opponent's hand cards are hidden unless revealed through gameplay

## License

Free to use and modify for personal use. No warranty provided.

## Contributing

This is a personal project, but feel free to fork and enhance!
