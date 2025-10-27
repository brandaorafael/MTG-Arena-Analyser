#!/usr/bin/env python3
"""
Enhanced MTG Arena Log Parser
Extracts game information including opponent cards when available
"""

import json
import re
from collections import defaultdict
from typing import Dict, List, Tuple, Optional, Any, Set, Iterator, Union

from src.type_definitions import CardInfo, InstanceLocation


class MatchParser:
    """Parser for MTG Arena game logs"""

    def __init__(self, log_path: str, match_id: str, card_db: Dict[str, CardInfo]) -> None:
        self.log_path: str = log_path
        self.match_id: str = match_id
        self.card_db: Dict[str, CardInfo] = card_db

        # Game state tracking
        self.player_seat_id: Optional[int] = None
        self.opponent_seat_id: Optional[int] = None
        self.opponent_name: Optional[str] = None
        self.instance_locations: Dict[int, InstanceLocation] = {}
        self.instance_id_map: Dict[int, int] = {}
        self.instance_to_grp: Dict[int, int] = {}
        self.final_player_hand: List[int] = []
        self.final_opponent_hand: List[int] = []
        self.player_deck: Dict[int, int] = defaultdict(int)
        self.opponent_deck: Dict[int, int] = defaultdict(int)
        self.opponent_deck_size: int = 0
        self.player_commander: Optional[int] = None
        self.opponent_commander: Optional[int] = None

        # Build split card normalization map
        self.split_card_grp_map: Dict[int, int] = self._build_split_card_map()

    def parse(self) -> Tuple[Dict[int, int], Dict[int, int]]:
        """Main parsing method"""
        print(f"Parsing detailed logs for match: {self.match_id[:8]}...")

        # Detect player seat
        self._detect_player_seat()

        # Extract opponent name
        self._extract_opponent_name()

        # Parse log file
        with open(self.log_path, 'r', encoding='utf-8', errors='ignore') as f:
            in_match: bool = False

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

    def _build_split_card_map(self) -> Dict[int, int]:
        """Build a map of split card half grpIds to full card grpIds"""
        grp_map: Dict[int, int] = {}
        full_cards: Dict[str, int] = {}  # name -> canonical grpId for full split cards
        full_card_grp_ids: Dict[str, List[int]] = {}  # name -> all grpIds for that full card

        # First pass: find all full split cards (both // and /// separators)
        # and track all grpIds for each unique card name
        for grp_id_str, card_info in self.card_db.items():
            name: str = card_info.get('name', '')
            grp_id: int = int(grp_id_str)
            if ' // ' in name or ' /// ' in name:
                if name not in full_cards:
                    full_cards[name] = grp_id  # Use first grpId as canonical
                    full_card_grp_ids[name] = []
                full_card_grp_ids[name].append(grp_id)

        # Map all duplicate full card grpIds to the canonical one
        for name, canonical_grp_id in full_cards.items():
            for grp_id in full_card_grp_ids[name]:
                if grp_id != canonical_grp_id:
                    grp_map[grp_id] = canonical_grp_id

        # Second pass: map halves to full cards
        for grp_id_str, card_info in self.card_db.items():
            name: str = card_info.get('name', '')
            grp_id: int = int(grp_id_str)

            # Check if this card name is a half of any split card
            for full_name, full_grp_id in full_cards.items():
                # Try both separator types
                separator: Optional[str] = None
                if ' // ' in full_name:
                    separator = ' // '
                elif ' /// ' in full_name:
                    separator = ' /// '

                if separator:
                    parts: List[str] = full_name.split(separator)
                    if name in [p.strip() for p in parts]:
                        # This is a half, map it to the full card
                        grp_map[grp_id] = full_grp_id
                        break

        return grp_map

    def _detect_player_seat(self) -> None:
        """Detect which seat ID belongs to the local player"""
        player_seat_id: Optional[int] = self._detect_seat_from_connect_resp()

        if player_seat_id is None:
            player_seat_id = self._detect_seat_from_reserved_players()

        if player_seat_id is None:
            print("⚠️  Could not determine player seat ID, assuming seat 1")
            player_seat_id = 1

        self.player_seat_id = player_seat_id
        self.opponent_seat_id = 2 if player_seat_id == 1 else 1

    def _detect_seat_from_connect_resp(self) -> Optional[int]:
        """Detect seat from messages with single systemSeatIds (sent only to local player)"""
        with open(self.log_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                if self.match_id not in line:
                    continue

                # Look for any message with systemSeatIds containing a single seat
                # These messages are only sent to the local player
                if '"systemSeatIds"' in line and '"greToClientEvent"' in line:
                    try:
                        data: Dict[str, Any] = json.loads(line)
                        gre_event: Dict[str, Any] = data.get('greToClientEvent', {})
                        messages: List[Dict[str, Any]] = gre_event.get('greToClientMessages', [])

                        for msg in messages:
                            seat_ids: List[int] = msg.get('systemSeatIds', [])
                            # If systemSeatIds has exactly one seat, that's the local player
                            if seat_ids and len(seat_ids) == 1:
                                print(f"You are seat {seat_ids[0]}")
                                return seat_ids[0]
                    except (json.JSONDecodeError, KeyError, TypeError, IndexError):
                        pass
        return None

    def _detect_seat_from_reserved_players(self) -> Optional[int]:
        """Fallback: detect seat from reservedPlayers list"""
        with open(self.log_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                if self.match_id not in line:
                    continue

                if '"reservedPlayers"' in line:
                    try:
                        data: Dict[str, Any] = json.loads(line)
                        game_room_event: Dict[str, Any] = data.get('matchGameRoomStateChangedEvent', {})
                        game_room_info: Dict[str, Any] = game_room_event.get('gameRoomInfo', {})
                        game_room_config: Dict[str, Any] = game_room_info.get('gameRoomConfig', {})
                        reserved_players: List[Dict[str, Any]] = game_room_config.get('reservedPlayers', [])

                        for player in reserved_players:
                            seat_id: Optional[int] = player.get('systemSeatId')
                            player_name: str = player.get('playerName', 'Unknown')
                            print(f"⚠️  Auto-detected seat {seat_id} (player: {player_name})")
                            print(f"⚠️  If this is incorrect, the card lists will be swapped")
                            return seat_id
                    except (json.JSONDecodeError, KeyError, TypeError):
                        pass
        return None

    def _extract_opponent_name(self) -> None:
        """Extract opponent's name from reservedPlayers"""
        with open(self.log_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                if self.match_id not in line:
                    continue

                if '"reservedPlayers"' in line:
                    try:
                        data: Dict[str, Any] = json.loads(line)
                        game_room_event: Dict[str, Any] = data.get('matchGameRoomStateChangedEvent', {})
                        game_room_info: Dict[str, Any] = game_room_event.get('gameRoomInfo', {})
                        game_room_config: Dict[str, Any] = game_room_info.get('gameRoomConfig', {})
                        reserved_players: List[Dict[str, Any]] = game_room_config.get('reservedPlayers', [])

                        for player in reserved_players:
                            seat_id: Optional[int] = player.get('systemSeatId')
                            player_name: str = player.get('playerName', 'Unknown')
                            if seat_id == self.opponent_seat_id:
                                self.opponent_name = player_name
                                return
                    except (json.JSONDecodeError, KeyError, TypeError):
                        pass

    def _build_instance_mappings(self, line: str) -> None:
        """Build instance ID to grpId mappings from a log line"""
        if '"grpId"' not in line or '"instanceId"' not in line:
            return

        object_pattern: str = r'\{\s*"instanceId"\s*:\s*(\d+)[^}]*"grpId"\s*:\s*(\d+)[^}]*\}|\{\s*"grpId"\s*:\s*(\d+)[^}]*"instanceId"\s*:\s*(\d+)[^}]*\}'
        for match in re.finditer(object_pattern, line):
            if match.group(1):  # instanceId first
                instance_id: int = int(match.group(1))
                grp_id: int = int(match.group(2))
            else:  # grpId first
                grp_id = int(match.group(3))
                instance_id = int(match.group(4))

            # Skip tokens (not in card database)
            if str(grp_id) not in self.card_db:
                continue

            # Normalize split cards: if this is a half, use the full card's grpId
            normalized_grp_id: int = self.split_card_grp_map.get(grp_id, grp_id)

            self.instance_to_grp[instance_id] = normalized_grp_id

    def _process_instance_id_changes(self, line: str) -> None:
        """Process ObjectIdChanged annotations"""
        if '"AnnotationType_ObjectIdChanged"' not in line:
            return

        id_changes: List[Tuple[int, int]] = []
        for orig_match, new_match in zip(
            re.finditer(r'"orig_id".*?"valueInt32"\s*:\s*\[\s*(\d+)\s*\]', line),
            re.finditer(r'"new_id".*?"valueInt32"\s*:\s*\[\s*(\d+)\s*\]', line)
        ):
            old_id: int = int(orig_match.group(1))
            new_id: int = int(new_match.group(1))
            id_changes.append((old_id, new_id))

        for old_id, new_id in id_changes:
            self.instance_id_map[old_id] = new_id
            if old_id in self.instance_to_grp:
                self.instance_to_grp[new_id] = self.instance_to_grp[old_id]

    def _extract_player_deck(self, line: str) -> None:
        """Extract player's starting deck from deckMessage"""
        if '"deckMessage"' not in line or '"deckCards"' not in line:
            return

        try:
            deck_match: Optional[re.Match[str]] = re.search(r'"deckCards"\s*:\s*\[\s*([0-9,\s]+)\s*\]', line)
            if deck_match:
                deck_cards_str: str = deck_match.group(1)
                deck_cards: List[int] = [int(x.strip()) for x in deck_cards_str.split(',') if x.strip()]
                for grp_id in deck_cards:
                    self.player_deck[grp_id] += 1
        except (ValueError, AttributeError):
            pass

    def _extract_opponent_deck_size(self, line: str) -> None:
        """Extract opponent's deck size from library zone (track maximum size seen)"""
        if '"ZoneType_Library"' not in line:
            return

        if '"ownerSeatId"' in line:
            if re.search(rf'"ownerSeatId"\s*:\s*{self.opponent_seat_id}', line):
                instance_ids_match: Optional[re.Match[str]] = re.search(r'"objectInstanceIds"\s*:\s*\[\s*([0-9,\s]+)\s*\]', line)
                if instance_ids_match:
                    instance_ids_str: str = instance_ids_match.group(1)
                    instance_ids: List[str] = [x.strip() for x in instance_ids_str.split(',') if x.strip()]
                    library_size: int = len(instance_ids)
                    # Keep the maximum library size (starting deck size)
                    if library_size > self.opponent_deck_size:
                        self.opponent_deck_size = library_size

    def _extract_commanders(self, line: str) -> None:
        """Extract commanders from command zone (zone 32 for seat 1, zone 34 for seat 2)"""
        if '"ZoneType_Command"' not in line:
            return

        try:
            data: Dict[str, Any] = json.loads(line)

            def find_zones(obj: Union[Dict[str, Any], List[Any]]) -> Iterator[Dict[str, Any]]:
                if isinstance(obj, dict):
                    if 'type' in obj and obj.get('type') == 'ZoneType_Command':
                        yield obj
                    for value in obj.values():
                        yield from find_zones(value)
                elif isinstance(obj, list):
                    for item in obj:
                        yield from find_zones(item)

            for zone_obj in find_zones(data):
                owner: Optional[int] = zone_obj.get('ownerSeatId')
                instance_ids: List[int] = zone_obj.get('objectInstanceIds', [])

                if not instance_ids:
                    continue

                # Get the first card in command zone (the commander)
                for inst_id in instance_ids:
                    if inst_id in self.instance_to_grp:
                        grp_id: int = self.instance_to_grp[inst_id]
                        if owner == self.player_seat_id and not self.player_commander:
                            self.player_commander = grp_id
                        elif owner == self.opponent_seat_id and not self.opponent_commander:
                            self.opponent_commander = grp_id
        except (json.JSONDecodeError, KeyError, TypeError):
            pass

    def _extract_hand_zones(self, line: str) -> None:
        """Extract hand zone contents"""
        if '"ZoneType_Hand"' not in line or '"objectInstanceIds"' not in line:
            return

        zone_pattern: str = r'\{\s*"zoneId"\s*:\s*(\d+)[^}]*"type"\s*:\s*"ZoneType_Hand"[^}]*"ownerSeatId"\s*:\s*(\d+)[^}]*"objectInstanceIds"\s*:\s*\[\s*([0-9,\s]+)\s*\][^}]*\}'
        for match in re.finditer(zone_pattern, line):
            zone_id: int = int(match.group(1))
            owner: int = int(match.group(2))
            ids_str: str = match.group(3)
            instance_ids: List[int] = [int(x.strip()) for x in ids_str.split(',') if x.strip()]

            if owner == self.player_seat_id:
                self.final_player_hand = instance_ids
            elif owner == self.opponent_seat_id:
                self.final_opponent_hand = instance_ids

    def find_game_objects(self, obj: Union[Dict[str, Any], List[Any]]) -> Iterator[List[Dict[str, Any]]]:
        """Recursively find all gameObjects arrays in JSON structure"""
        if isinstance(obj, dict):
            if 'gameObjects' in obj and isinstance(obj['gameObjects'], list):
                yield obj['gameObjects']
            for value in obj.values():
                yield from self.find_game_objects(value)
        elif isinstance(obj, list):
            for item in obj:
                yield from self.find_game_objects(item)

    def _track_instance_locations(self, line: str) -> None:
        """Track current location of card instances"""
        if '"gameObjects"' not in line or '"instanceId"' not in line:
            return

        try:
            data: Dict[str, Any] = json.loads(line)

            for game_objects_list in self.find_game_objects(data):
                for obj in game_objects_list:
                    if not isinstance(obj, dict):
                        continue

                    instance_id: Optional[int] = obj.get('instanceId')
                    grp_id: Optional[int] = obj.get('grpId')
                    owner: Optional[int] = obj.get('ownerSeatId')
                    zone_id: Optional[int] = obj.get('zoneId')
                    visibility: str = obj.get('visibility', '')

                    if instance_id is None or grp_id is None:
                        continue
                    if str(grp_id) not in self.card_db:
                        continue

                    # Normalize split cards
                    normalized_grp_id: int = self.split_card_grp_map.get(grp_id, grp_id)

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

    def _count_revealed_cards(self) -> Tuple[Dict[int, int], Dict[int, int]]:
        """Count cards from all tracked zones with unified deduplication logic"""
        player_cards: Dict[int, int] = defaultdict(int)
        opponent_cards: Dict[int, int] = defaultdict(int)

        # Relevant zones to count (permanent locations only):
        # Zone 28=Battlefield, 29=Exile
        # Zone 31=Seat 1's hand, 35=Seat 2's hand
        # Zone 33=Seat 1's graveyard, 37=Seat 2's graveyard
        # Excluded zones:
        #   Zone 30 (library) - can't distinguish seen vs unseen cards
        #   Zone 32/34 (revealed/command) - temporary zones, cards pass through
        relevant_zones: List[int] = [28, 29, 31, 33, 35, 37]

        # Only count terminal instances (not replaced via ObjectIdChanged)
        # This filters out cards from mulligan and intermediate zone transitions
        obsolete_instances: Set[int] = set(self.instance_id_map.keys())

        # Instances that are part of ObjectIdChanged chains
        instances_with_history: Set[int] = set(self.instance_id_map.values())

        # Build map of each instance to its FINAL location
        # This ensures we only count each instance once from its last known zone
        instance_final_location: Dict[int, InstanceLocation] = {}

        # Valid instances are those that either:
        # 1. Went through ObjectIdChanged (instances_with_history), OR
        # 2. Are in the current actual hand (final_player_hand / final_opponent_hand)
        valid_instances: Set[int] = instances_with_history.copy()
        valid_instances.update(self.final_player_hand)
        valid_instances.update(self.final_opponent_hand)

        for instance_id, location in self.instance_locations.items():
            # Skip obsolete instances (replaced by newer instance IDs)
            if instance_id in obsolete_instances:
                continue

            # Only count valid instances (filters out stale mulligan instances)
            if instance_id not in valid_instances:
                continue

            zone: Optional[int] = location['zone']
            if zone not in relevant_zones:
                continue

            # Track this as the final location for this instance
            # (will overwrite if seen multiple times, keeping the last one)
            instance_final_location[instance_id] = location

        # Now count from final locations, deduplicating split cards
        zone_cards: Dict[Tuple[int, Optional[int], Optional[int]], Set[int]] = defaultdict(set)

        for instance_id, location in instance_final_location.items():
            grp_id: int = location['grpId']
            owner: Optional[int] = location['owner']
            zone: Optional[int] = location['zone']

            # Track by zone to deduplicate split cards (same grpId, owner, zone)
            zone_key: Tuple[int, Optional[int], Optional[int]] = (grp_id, owner, zone)
            zone_cards[zone_key].add(instance_id)

        # Count the number of physical cards for each (grpId, owner, zone)
        for (grp_id, owner, zone), instance_set in zone_cards.items():
            num_copies: int = len(instance_set)

            # Skip if this grpId is a split card half (it should already be counted under the full card)
            if grp_id in self.split_card_grp_map:
                continue

            if owner == self.player_seat_id:
                player_cards[grp_id] += num_copies
            elif owner == self.opponent_seat_id:
                opponent_cards[grp_id] += num_copies

        return player_cards, opponent_cards
