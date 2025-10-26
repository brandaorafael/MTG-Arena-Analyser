# MTG Arena Log Parser

Custom-built tools to extract and analyze MTG Arena match data from detailed logs.

## ✨ Features

- **Automatic player seat detection** - Works for any player without hardcoded usernames
- **Complete deck tracking** - Shows both your revealed cards and opponent's revealed cards
- **Multi-zone tracking** - Tracks cards in hand, battlefield, graveyard, and exile
- **Accurate card counts** - Correctly counts duplicate cards
- **Deck statistics** - Shows revealed vs unrevealed card breakdown
- **Real-time monitoring** - Optional live match tracking

## 📁 Files

- **parse-mtga-logs.sh** - Main parser wrapper (finds most recent match and parses it)
- **parse_cards_enhanced.py** - Enhanced parser with full game state tracking
- **extract_card_database.py** - Extracts MTGA's card database to JSON
- **monitor_match.py** - Real-time match monitor (shows cards as they're played)
- **parse_cards.py** - Legacy parser (basic functionality)
- **card_database.json** - 21,477 cards extracted from MTGA's SQLite database

## 🚀 Quick Start

### Step 1: Extract Card Database (One-time setup)

```bash
cd ~/Projects/MTGArena
./extract_card_database.py
```

This creates `card_database.json` with all MTG Arena cards.

### Step 2: Enable Detailed Logging

**IMPORTANT:** You must enable detailed logging in MTG Arena:

1. Launch MTG Arena
2. Click the gear icon (⚙️) in the top right
3. Go to **View Account** (bottom of settings menu)
4. Enable **Detailed Logs (Plugin Support)**
5. Restart MTG Arena

Without detailed logging, the parser cannot extract card information.

### Step 3: Play a Match

Play a match in MTG Arena with detailed logging enabled.

### Step 4: Analyze the Match

```bash
./parse-mtga-logs.sh
```

This will automatically find and parse the most recent match.

## 📊 What the Parser Shows

### Your Deck
- All cards you've revealed (in hand or played)
- Accurate card counts
- Full deck size and revealed/unrevealed breakdown

### Opponent's Deck
- All cards opponent has revealed
- Cards from battlefield, graveyard, and exile
- Cards they've played or discarded
- Full deck size and revealed/unrevealed breakdown

### Example Output

```
🔍 MTG Arena Match Log Parser
================================

🎮 Finding most recent match...
Match ID: f757d013-ca82-4035-bde0-3cc64a40017e

✅ Loaded 21477 cards from database

📖 Parsing detailed logs for match: f757d013...
🎮 You are seat 2

============================================================
🃏 YOUR DECK
============================================================

📦 REVEALED CARDS:

   1. Ajani's Pridemate
   2. Essence Channeler (x2)
   3. Haliya, Guided by Light
   4. Hinterland Sanctifier
   5. Mountain
   6. Waystone's Guidance
   7. Wind-Scarred Crag (x3)

📊 Deck: 60 cards total | 10 revealed | 50 unrevealed

============================================================
🎴 OPPONENT'S DECK
============================================================

📦 REVEALED CARDS:

   1. A-Cori-Steel Cutter (x2)
   2. Into the Flood Maw
   3. Island
   4. Multiversal Passage
   5. Opt (x2)
   6. Riverpyre Verge (x2)
   7. Stormchaser's Talent
   8. Wild Ride

📊 Deck: 60 cards total | 11 revealed | 49 unrevealed
```

## 🎯 Advanced Usage

### Parse a Specific Match

```bash
python3 parse_cards_enhanced.py /path/to/Player.log <match-id>
```

### Real-Time Monitor

Monitor matches as they happen:

```bash
./monitor_match.py
```

This shows cards in real-time as they're played during the match.

## 🗄️ Card Database

The `card_database.json` contains:
- **21,477 cards** from MTG Arena
- Card IDs (grpId), names, expansions, and collector numbers
- Extracted directly from MTGA's SQLite database

Location: `~/Library/Application Support/com.wizards.mtga/Downloads/Raw/Raw_CardDatabase_*.mtga`

## 📍 Log File Locations

**Player Log:**
```
~/Library/Logs/Wizards Of The Coast/MTGA/Player.log
```

**MTGA Card Database:**
```
~/Library/Application Support/com.wizards.mtga/Downloads/Raw/Raw_CardDatabase_*.mtga
```

**Match History Logs:**
```
~/Library/Application Support/com.wizards.mtga/Logs/Logs/UTC_Log - *.log
```

## 🛠 Technical Details

### How It Works

1. **Automatic Seat Detection**: Uses `GREMessageType_ConnectResp` to identify which seat is the local player
2. **Instance Tracking**: Tracks all card instances and their grpId mappings
3. **Location Tracking**: Monitors cards as they move between zones (hand, battlefield, graveyard, exile)
4. **Zone Parsing**: Uses explicit zone lists for hand contents (most reliable)
5. **JSON Parsing**: Properly handles deeply nested game objects with arrays/abilities

### Zones Tracked

- **Zone 28**: Battlefield (public)
- **Zone 29**: Exile (public)
- **Zone 31**: Seat 1's hand (private for seat 1, hidden for seat 2)
- **Zone 33**: Seat 1's graveyard (public)
- **Zone 35**: Seat 2's hand (private for seat 2, hidden for seat 1)
- **Zone 37**: Seat 2's graveyard (public)

### Card Database Structure

The MTGA card database is a SQLite 3 database with tables:
- `Cards` - All card data (grpId, titleId, rarity, types, etc.)
- `Localizations_enUS` - English card names and text
- `Abilities` - Card ability definitions
- `Enums` - Game enumerations

### Log Format (Detailed Logging)

```json
{
  "greToClientEvent": {
    "greToClientMessages": [
      {
        "type": "GREMessageType_GameStateMessage",
        "gameStateMessage": {
          "gameObjects": [
            {
              "instanceId": 312,
              "grpId": 91548,
              "ownerSeatId": 2,
              "zoneId": 28,
              "visibility": "Visibility_Public"
            }
          ]
        }
      }
    ]
  }
}
```

The `grpId` maps to the card database, `ownerSeatId` identifies the owner, and `zoneId` indicates location.

## 🔧 Key Implementation Details

### Accurate Card Counting

The parser tracks the **current location** of each card instance:
- Uses explicit `objectInstanceIds` arrays from zone messages (authoritative for hand contents)
- Tracks `gameObjects` for battlefield, graveyard, and exile
- Only counts cards in their **final** location (not historical appearances)
- Resolves instance ID changes via `ObjectIdChanged` annotations

### Instance ID Mapping

Cards can change instance IDs as they move between zones:
```
Original ID: 284 -> New ID: 289 (when moving from hand to battlefield)
```

The parser tracks these changes and maps them correctly.

### Seat Assignment

Player seats are **not fixed** - they vary per match:
- Sometimes player is seat 1, sometimes seat 2
- Parser automatically detects correct assignment
- Works for any player without hardcoded usernames

## 🚨 Important Notes

### Detailed Logging Required

**The parser REQUIRES detailed logging to be enabled** in MTG Arena. Without it:
- No grpId data in logs
- Cannot identify cards
- Only basic match flow available

### Privacy Considerations

- All parsing is done locally on your machine
- No data is sent to external servers
- Card database is extracted from your local MTGA installation

### Limitations

- Only tracks cards that have been revealed (played, discarded, or drawn into hand)
- Cannot see opponent's unrevealed cards in library
- Opponent's hand cards are hidden unless they've been revealed

## 📝 Example Usage

```bash
# Extract card database (one time)
./extract_card_database.py

# Enable detailed logging in MTGA settings (one time)

# Play a match

# Parse the most recent match
./parse-mtga-logs.sh

# Or monitor live
./monitor_match.py
```

## 🔬 Research Findings

1. **MTGA uses SQLite** for its card database - fully accessible
2. **Logs use two ID systems:**
   - `grpId`: Permanent card ID (maps to database)
   - `instanceId`: Per-match runtime ID
3. **Instance IDs can change** during a match via `ObjectIdChanged` annotations
4. **Seat assignment varies** - must be detected dynamically per match
5. **Zone lists are authoritative** for hand contents
6. **Game objects can be deeply nested** - requires proper JSON parsing, not regex

## 📜 License

Free to use and modify for personal use. No warranty provided.

## 🤝 Contributing

This is a personal project, but feel free to fork and enhance!
