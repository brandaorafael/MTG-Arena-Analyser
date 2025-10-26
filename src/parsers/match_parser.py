#!/usr/bin/env python3
"""
Enhanced MTG Arena Log Parser
Extracts game information including opponent cards when available
"""

import json
import re
from collections import defaultdict


class MatchParser:
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
        self.player_commander = None
        self.opponent_commander = None

        # Build split card normalization map
        self.split_card_grp_map = self._build_split_card_map()

    def parse(self):
        """Main parsing method"""
        print(f"📖 Parsing detailed logs for match: {self.match_id[:8]}...")

        # Detect player seat
        self._detect_player_seat()

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
                self._build_instance_mappings(line)
                self._process_instance_id_changes(line)
                self._extract_player_deck(line)
                self._extract_opponent_deck_size(line)
                self._extract_commanders(line)
                self._extract_hand_zones(line)
                self._track_instance_locations(line)

        # Count revealed cards
        player_cards, opponent_cards = self._count_revealed_cards()

        return player_cards, opponent_cards

    def _build_split_card_map(self):
        """Build a map of split card half grpIds to full card grpIds"""
        grp_map = {}
        full_cards = {}  # name -> grpId for full split cards

        # First pass: find all full split cards
        for grp_id_str, card_info in self.card_db.items():
            name = card_info.get('name', '')
            if ' /// ' in name:
                full_cards[name] = int(grp_id_str)

        # Second pass: map halves to full cards
        for grp_id_str, card_info in self.card_db.items():
            name = card_info.get('name', '')
            grp_id = int(grp_id_str)

            # Check if this card name is a half of any split card
            for full_name, full_grp_id in full_cards.items():
                if ' /// ' in full_name:
                    parts = full_name.split(' /// ')
                    if name in [p.strip() for p in parts]:
                        # This is a half, map it to the full card
                        grp_map[grp_id] = full_grp_id
                        break

        return grp_map

    def _detect_player_seat(self):
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

    def _build_instance_mappings(self, line):
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

            # Normalize split cards: if this is a half, use the full card's grpId
            normalized_grp_id = self.split_card_grp_map.get(grp_id, grp_id)

            self.instance_to_grp[instance_id] = normalized_grp_id

    def _process_instance_id_changes(self, line):
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

    def _extract_player_deck(self, line):
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

    def _extract_opponent_deck_size(self, line):
        """Extract opponent's deck size from library zone (track maximum size seen)"""
        if '"ZoneType_Library"' not in line:
            return

        if '"ownerSeatId"' in line:
            if re.search(rf'"ownerSeatId"\s*:\s*{self.opponent_seat_id}', line):
                instance_ids_match = re.search(r'"objectInstanceIds"\s*:\s*\[\s*([0-9,\s]+)\s*\]', line)
                if instance_ids_match:
                    instance_ids_str = instance_ids_match.group(1)
                    instance_ids = [x.strip() for x in instance_ids_str.split(',') if x.strip()]
                    library_size = len(instance_ids)
                    # Keep the maximum library size (starting deck size)
                    if library_size > self.opponent_deck_size:
                        self.opponent_deck_size = library_size

    def _extract_commanders(self, line):
        """Extract commanders from command zone (zone 32 for seat 1, zone 34 for seat 2)"""
        if '"ZoneType_Command"' not in line:
            return

        try:
            data = json.loads(line)

            def find_zones(obj):
                if isinstance(obj, dict):
                    if 'type' in obj and obj.get('type') == 'ZoneType_Command':
                        yield obj
                    for value in obj.values():
                        yield from find_zones(value)
                elif isinstance(obj, list):
                    for item in obj:
                        yield from find_zones(item)

            for zone_obj in find_zones(data):
                owner = zone_obj.get('ownerSeatId')
                instance_ids = zone_obj.get('objectInstanceIds', [])

                if not instance_ids:
                    continue

                # Get the first card in command zone (the commander)
                for inst_id in instance_ids:
                    if inst_id in self.instance_to_grp:
                        grp_id = self.instance_to_grp[inst_id]
                        if owner == self.player_seat_id and not self.player_commander:
                            self.player_commander = grp_id
                        elif owner == self.opponent_seat_id and not self.opponent_commander:
                            self.opponent_commander = grp_id
        except (json.JSONDecodeError, KeyError, TypeError):
            pass

    def _extract_hand_zones(self, line):
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

    def _track_instance_locations(self, line):
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

                    # Normalize split cards
                    normalized_grp_id = self.split_card_grp_map.get(grp_id, grp_id)

                    # Check for commanders in command zone (zone 32 for seat 1, zone 34 for seat 2)
                    # Zone 32 = Seat 1 command zone, Zone 34 = Seat 2 command zone
                    if zone_id in [32, 34]:
                        if owner == self.player_seat_id and not self.player_commander:
                            self.player_commander = normalized_grp_id
                        elif owner == self.opponent_seat_id and not self.opponent_commander:
                            self.opponent_commander = normalized_grp_id

                    # Only track visible cards
                    if visibility == "Visibility_Public" or owner == self.player_seat_id:
                        self.instance_locations[instance_id] = {
                            'grpId': normalized_grp_id,
                            'zone': zone_id,
                            'owner': owner,
                            'visibility': visibility
                        }
        except (json.JSONDecodeError, KeyError, TypeError):
            pass

    def _count_revealed_cards(self):
        """Count cards from all tracked zones with unified deduplication logic"""
        player_cards = defaultdict(int)
        opponent_cards = defaultdict(int)

        # Relevant zones to count (permanent locations only):
        # Zone 28=Battlefield, 29=Exile
        # Zone 31=Seat 1's hand, 35=Seat 2's hand
        # Zone 33=Seat 1's graveyard, 37=Seat 2's graveyard
        # Excluded zones:
        #   Zone 30 (library) - can't distinguish seen vs unseen cards
        #   Zone 32/34 (revealed/command) - temporary zones, cards pass through
        relevant_zones = [28, 29, 31, 33, 35, 37]

        # Only count terminal instances (not replaced via ObjectIdChanged)
        # This filters out cards from mulligan and intermediate zone transitions
        obsolete_instances = set(self.instance_id_map.keys())

        # Instances that are part of ObjectIdChanged chains
        instances_with_history = set(self.instance_id_map.values())

        # Build map of each instance to its FINAL location
        # This ensures we only count each instance once from its last known zone
        instance_final_location = {}

        for instance_id, location in self.instance_locations.items():
            # Skip obsolete instances (replaced by newer instance IDs)
            if instance_id in obsolete_instances:
                continue

            # Only count instances that are part of ObjectIdChanged chains
            # This filters out orphaned split card halves and temporary revealed instances
            if instance_id not in instances_with_history:
                continue

            zone = location['zone']
            if zone not in relevant_zones:
                continue

            # Track this as the final location for this instance
            # (will overwrite if seen multiple times, keeping the last one)
            instance_final_location[instance_id] = location

        # Now count from final locations, deduplicating split cards
        zone_cards = defaultdict(set)

        for instance_id, location in instance_final_location.items():
            grp_id = location['grpId']
            owner = location['owner']
            zone = location['zone']

            # Track by zone to deduplicate split cards (same grpId, owner, zone)
            zone_key = (grp_id, owner, zone)
            zone_cards[zone_key].add(instance_id)

        # Count the number of physical cards for each (grpId, owner, zone)
        for (grp_id, owner, zone), instance_set in zone_cards.items():
            num_copies = len(instance_set)

            if owner == self.player_seat_id:
                player_cards[grp_id] += num_copies
            elif owner == self.opponent_seat_id:
                opponent_cards[grp_id] += num_copies

        return player_cards, opponent_cards
