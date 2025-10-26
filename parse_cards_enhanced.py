#!/usr/bin/env python3
"""
Enhanced MTG Arena Log Parser
Extracts game information including opponent cards when available
"""

import sys
import json
import re
import os
from collections import defaultdict


class MTGArenaLogParser:
    """Parser for MTG Arena game logs"""

    def __init__(self, log_path, match_id, card_db):
        self.log_path = log_path
        self.match_id = match_id
        self.card_db = card_db

        # Game state tracking
        self.player_seat_id = None
        self.opponent_seat_id = None
        self.instance_locations = {}
        self.instance_id_map = {}
        self.instance_to_grp = {}
        self.final_player_hand = []
        self.final_opponent_hand = []
        self.player_deck = defaultdict(int)
        self.opponent_deck = defaultdict(int)
        self.opponent_deck_size = 0

    def detect_player_seat(self):
        """Detect which seat ID belongs to the local player"""
        player_seat_id = self._detect_seat_from_connect_resp()

        if player_seat_id is None:
            player_seat_id = self._detect_seat_from_reserved_players()

        if player_seat_id is None:
            print("⚠️  Could not determine player seat ID, assuming seat 1")
            player_seat_id = 1

        self.player_seat_id = player_seat_id
        self.opponent_seat_id = 2 if player_seat_id == 1 else 1

    def _detect_seat_from_connect_resp(self):
        """Detect seat from GREMessageType_ConnectResp message"""
        with open(self.log_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                if self.match_id not in line:
                    continue

                if '"GREMessageType_ConnectResp"' in line and '"systemSeatIds"' in line:
                    try:
                        data = json.loads(line)
                        gre_event = data.get('greToClientEvent', {})
                        messages = gre_event.get('greToClientMessages', [])

                        for msg in messages:
                            if msg.get('type') == 'GREMessageType_ConnectResp':
                                seat_ids = msg.get('systemSeatIds', [])
                                if seat_ids and len(seat_ids) == 1:
                                    print(f"🎮 You are seat {seat_ids[0]}")
                                    return seat_ids[0]
                    except (json.JSONDecodeError, KeyError, TypeError, IndexError):
                        pass
        return None

    def _detect_seat_from_reserved_players(self):
        """Fallback: detect seat from reservedPlayers list"""
        with open(self.log_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                if self.match_id not in line:
                    continue

                if '"reservedPlayers"' in line:
                    try:
                        data = json.loads(line)
                        game_room_event = data.get('matchGameRoomStateChangedEvent', {})
                        game_room_info = game_room_event.get('gameRoomInfo', {})
                        game_room_config = game_room_info.get('gameRoomConfig', {})
                        reserved_players = game_room_config.get('reservedPlayers', [])

                        for player in reserved_players:
                            seat_id = player.get('systemSeatId')
                            player_name = player.get('playerName', 'Unknown')
                            print(f"⚠️  Auto-detected seat {seat_id} (player: {player_name})")
                            print(f"⚠️  If this is incorrect, the card lists will be swapped")
                            return seat_id
                    except (json.JSONDecodeError, KeyError, TypeError):
                        pass
        return None

    def build_instance_mappings(self, line):
        """Build instance ID to grpId mappings from a log line"""
        if '"grpId"' not in line or '"instanceId"' not in line:
            return

        object_pattern = r'\{\s*"instanceId"\s*:\s*(\d+)[^}]*"grpId"\s*:\s*(\d+)[^}]*\}|\{\s*"grpId"\s*:\s*(\d+)[^}]*"instanceId"\s*:\s*(\d+)[^}]*\}'
        for match in re.finditer(object_pattern, line):
            if match.group(1):  # instanceId first
                instance_id = int(match.group(1))
                grp_id = int(match.group(2))
            else:  # grpId first
                grp_id = int(match.group(3))
                instance_id = int(match.group(4))

            # Skip tokens (not in card database)
            if str(grp_id) not in self.card_db:
                continue

            self.instance_to_grp[instance_id] = grp_id

    def process_instance_id_changes(self, line):
        """Process ObjectIdChanged annotations"""
        if '"AnnotationType_ObjectIdChanged"' not in line:
            return

        id_changes = []
        for orig_match, new_match in zip(
            re.finditer(r'"orig_id".*?"valueInt32"\s*:\s*\[\s*(\d+)\s*\]', line),
            re.finditer(r'"new_id".*?"valueInt32"\s*:\s*\[\s*(\d+)\s*\]', line)
        ):
            old_id = int(orig_match.group(1))
            new_id = int(new_match.group(1))
            id_changes.append((old_id, new_id))

        for old_id, new_id in id_changes:
            self.instance_id_map[old_id] = new_id
            if old_id in self.instance_to_grp:
                self.instance_to_grp[new_id] = self.instance_to_grp[old_id]

    def extract_player_deck(self, line):
        """Extract player's starting deck from deckMessage"""
        if '"deckMessage"' not in line or '"deckCards"' not in line:
            return

        try:
            deck_match = re.search(r'"deckCards"\s*:\s*\[\s*([0-9,\s]+)\s*\]', line)
            if deck_match:
                deck_cards_str = deck_match.group(1)
                deck_cards = [int(x.strip()) for x in deck_cards_str.split(',') if x.strip()]
                for grp_id in deck_cards:
                    self.player_deck[grp_id] += 1
        except (ValueError, AttributeError):
            pass

    def extract_opponent_deck_size(self, line):
        """Extract opponent's deck size from library zone"""
        if '"ZoneType_Library"' not in line or self.opponent_deck_size:
            return

        if '"ownerSeatId"' in line:
            if re.search(rf'"ownerSeatId"\s*:\s*{self.opponent_seat_id}', line):
                instance_ids_match = re.search(r'"objectInstanceIds"\s*:\s*\[\s*([0-9,\s]+)\s*\]', line)
                if instance_ids_match:
                    instance_ids_str = instance_ids_match.group(1)
                    instance_ids = [x.strip() for x in instance_ids_str.split(',') if x.strip()]
                    self.opponent_deck_size = len(instance_ids)

    def extract_hand_zones(self, line):
        """Extract hand zone contents"""
        if '"ZoneType_Hand"' not in line or '"objectInstanceIds"' not in line:
            return

        zone_pattern = r'\{\s*"zoneId"\s*:\s*(\d+)[^}]*"type"\s*:\s*"ZoneType_Hand"[^}]*"ownerSeatId"\s*:\s*(\d+)[^}]*"objectInstanceIds"\s*:\s*\[\s*([0-9,\s]+)\s*\][^}]*\}'
        for match in re.finditer(zone_pattern, line):
            zone_id = int(match.group(1))
            owner = int(match.group(2))
            ids_str = match.group(3)
            instance_ids = [int(x.strip()) for x in ids_str.split(',') if x.strip()]

            if owner == self.player_seat_id:
                self.final_player_hand = instance_ids
            elif owner == self.opponent_seat_id:
                self.final_opponent_hand = instance_ids

    def find_game_objects(self, obj):
        """Recursively find all gameObjects arrays in JSON structure"""
        if isinstance(obj, dict):
            if 'gameObjects' in obj and isinstance(obj['gameObjects'], list):
                yield obj['gameObjects']
            for value in obj.values():
                yield from self.find_game_objects(value)
        elif isinstance(obj, list):
            for item in obj:
                yield from self.find_game_objects(item)

    def track_instance_locations(self, line):
        """Track current location of card instances"""
        if '"gameObjects"' not in line or '"instanceId"' not in line:
            return

        try:
            data = json.loads(line)

            for game_objects_list in self.find_game_objects(data):
                for obj in game_objects_list:
                    if not isinstance(obj, dict):
                        continue

                    instance_id = obj.get('instanceId')
                    grp_id = obj.get('grpId')
                    owner = obj.get('ownerSeatId')
                    zone_id = obj.get('zoneId')
                    visibility = obj.get('visibility', '')

                    if instance_id is None or grp_id is None:
                        continue
                    if str(grp_id) not in self.card_db:
                        continue

                    # Only track visible cards
                    if visibility == "Visibility_Public" or owner == self.player_seat_id:
                        self.instance_locations[instance_id] = {
                            'grpId': grp_id,
                            'zone': zone_id,
                            'owner': owner,
                            'visibility': visibility
                        }
        except (json.JSONDecodeError, KeyError, TypeError):
            pass

    def count_revealed_cards(self):
        """Count cards from hand and visible zones"""
        player_cards = defaultdict(int)
        opponent_cards = defaultdict(int)

        # Add cards from hand zones
        for inst_id in self.final_player_hand:
            if inst_id in self.instance_to_grp:
                grp_id = self.instance_to_grp[inst_id]
                player_cards[grp_id] += 1

        for inst_id in self.final_opponent_hand:
            if inst_id in self.instance_to_grp:
                grp_id = self.instance_to_grp[inst_id]
                opponent_cards[grp_id] += 1

        # Add cards from visible zones: battlefield, graveyard, exile
        # Zone 28=Battlefield, 29=Exile, 33=Player Graveyard, 37=Opponent Graveyard
        for instance_id, location in self.instance_locations.items():
            zone = location['zone']
            if zone not in [28, 29, 33, 37]:
                continue

            grp_id = location['grpId']
            owner = location['owner']

            if owner == self.player_seat_id:
                player_cards[grp_id] += 1
            elif owner == self.opponent_seat_id:
                opponent_cards[grp_id] += 1

        return player_cards, opponent_cards

    def parse(self):
        """Main parsing method"""
        print(f"📖 Parsing detailed logs for match: {self.match_id[:8]}...")

        # Detect player seat
        self.detect_player_seat()

        # Parse log file
        with open(self.log_path, 'r', encoding='utf-8', errors='ignore') as f:
            in_match = False

            for line in f:
                if self.match_id in line:
                    in_match = True

                if not in_match:
                    continue

                # Check if different match started
                if 'matchId' in line and self.match_id not in line:
                    break

                # Process each line
                self.build_instance_mappings(line)
                self.process_instance_id_changes(line)
                self.extract_player_deck(line)
                self.extract_opponent_deck_size(line)
                self.extract_hand_zones(line)
                self.track_instance_locations(line)

        # Count revealed cards
        player_cards, opponent_cards = self.count_revealed_cards()

        return player_cards, opponent_cards


class OutputFormatter:
    """Format and display parsed results"""

    @staticmethod
    def format_card_list(cards, card_db):
        """Format a dictionary of cards into sorted list with names"""
        card_list = []
        for grp_id, count in cards.items():
            card_info = card_db.get(str(grp_id))
            if card_info:
                name = card_info['name']
                card_list.append((name, count, grp_id))
        return sorted(card_list)

    @staticmethod
    def print_card_list(card_list):
        """Print a formatted card list"""
        for i, (name, count, grp_id) in enumerate(card_list, 1):
            if count > 1:
                print(f"  {i:2d}. {name} (x{count})")
            else:
                print(f"  {i:2d}. {name}")

    @staticmethod
    def display_player_deck(player_cards, player_deck, card_db):
        """Display player's deck information"""
        print("")
        print("=" * 60)
        print("🃏 YOUR DECK")
        print("=" * 60)
        print("")

        if player_deck:
            total_cards = sum(player_deck.values())
            revealed_count = sum(player_cards.values())

            print("📦 REVEALED CARDS:")
            print("")

            if player_cards:
                card_list = OutputFormatter.format_card_list(player_cards, card_db)
                OutputFormatter.print_card_list(card_list)
            else:
                print("  (None)")

            print("")
            unrevealed = total_cards - revealed_count
            print(f"📊 Deck: {total_cards} cards total | {revealed_count} revealed | {unrevealed} unrevealed")

        elif player_cards:
            card_list = OutputFormatter.format_card_list(player_cards, card_db)
            OutputFormatter.print_card_list(card_list)
            print("")
            print(f"📊 Total: {len(player_cards)} unique cards revealed")
        else:
            print("No cards found")

    @staticmethod
    def display_opponent_deck(opponent_cards, opponent_deck_size, card_db):
        """Display opponent's deck information"""
        print("")
        print("=" * 60)
        print("🎴 OPPONENT'S DECK")
        print("=" * 60)
        print("")

        if opponent_cards:
            print("📦 REVEALED CARDS:")
            print("")

            card_list = OutputFormatter.format_card_list(opponent_cards, card_db)
            OutputFormatter.print_card_list(card_list)

            print("")
            revealed_count = sum(opponent_cards.values())

            if opponent_deck_size > 0:
                unrevealed = opponent_deck_size - revealed_count
                print(f"📊 Deck: {opponent_deck_size} cards total | {revealed_count} revealed | {unrevealed} unrevealed")
            else:
                print(f"📊 Revealed: {len(opponent_cards)} unique cards | {revealed_count} total cards seen")
                print(f"⚠️  Opponent deck size unknown")
        else:
            if opponent_deck_size > 0:
                print(f"No cards revealed (opponent has {opponent_deck_size} cards in deck)")
            else:
                print("No opponent cards found")

        print("")
        print("=" * 60)


def load_card_database():
    """Load the extracted card database"""
    db_path = os.path.expanduser("~/Projects/MTGArena/card_database.json")
    if not os.path.exists(db_path):
        print("⚠️  Card database not found. Run: ./extract_card_database.py")
        return {}

    with open(db_path, 'r') as f:
        return json.load(f)


def check_detailed_logging_enabled(log_file):
    """Check if detailed logging is enabled"""
    with open(log_file, 'r') as f:
        first_lines = f.read(1000)
        return "DETAILED LOGS: DISABLED" not in first_lines


def parse_basic_log(log_path, match_id):
    """Parse basic log information when detailed logging is not enabled"""
    print(f"📖 Parsing logs for match: {match_id[:8]}...")
    print("")
    print("=" * 60)
    print("⚠️  DETAILED LOGGING NOT ENABLED")
    print("=" * 60)
    print("")
    print("To use this parser, you must enable detailed logging in MTG Arena:")
    print("")
    print("1. Launch MTG Arena")
    print("2. Click the gear icon (⚙️) in the top right")
    print("3. Go to 'View Account' (bottom of settings menu)")
    print("4. Enable 'Detailed Logs (Plugin Support)'")
    print("5. Restart MTG Arena")
    print("")


def main():
    """Main entry point"""
    if len(sys.argv) < 3:
        print("Usage: parse_cards_enhanced.py <log_file> <match_id>")
        sys.exit(1)

    log_file = sys.argv[1]
    match_id = sys.argv[2]

    # Load card database
    card_db = load_card_database()
    if card_db:
        print(f"✅ Loaded {len(card_db)} cards from database")
        print("")

    # Check if detailed logging is enabled
    if not check_detailed_logging_enabled(log_file):
        parse_basic_log(log_file, match_id)
        return

    # Parse the match
    parser = MTGArenaLogParser(log_file, match_id, card_db)
    player_cards, opponent_cards = parser.parse()

    # Display results
    if opponent_cards or player_cards or parser.player_deck:
        OutputFormatter.display_player_deck(player_cards, parser.player_deck, card_db)
        OutputFormatter.display_opponent_deck(opponent_cards, parser.opponent_deck_size, card_db)
    else:
        parse_basic_log(log_file, match_id)


if __name__ == "__main__":
    main()
