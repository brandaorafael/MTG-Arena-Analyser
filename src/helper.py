import re
import json
from typing import List, Dict, Optional
from datetime import datetime


class Helper:
    """Helper functions"""

    @staticmethod
    def check_detailed_logging_enabled(log_file: str) -> bool:
        """Check if detailed logging is enabled"""
        with open(log_file, 'r') as f:
            first_lines: str = f.read(1000)
            return "DETAILED LOGS: DISABLED" not in first_lines

    @staticmethod
    def get_all_match_ids(log_file: str) -> List[Dict[str, Optional[str]]]:
        """Extract all match IDs with metadata from the log file"""
        matches: Dict[str, Dict[str, Optional[str]]] = {}

        with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                # Look for match IDs in JSON data
                if 'matchId' in line and '{' in line:
                    try:
                        data = json.loads(line)

                        # Check if this is a matchGameRoomStateChangedEvent
                        if 'matchGameRoomStateChangedEvent' in data:
                            event = data['matchGameRoomStateChangedEvent']
                            game_room = event.get('gameRoomInfo', {})
                            config = game_room.get('gameRoomConfig', {})
                            match_id = config.get('matchId')

                            if not match_id:
                                continue

                            # Initialize match if not seen
                            if match_id not in matches:
                                matches[match_id] = {
                                    'match_id': match_id,
                                    'start_time': None,
                                    'end_time': None,
                                    'opponent_name': None
                                }

                            # Get timestamp
                            timestamp_ms = data.get('timestamp')
                            if timestamp_ms:
                                timestamp = datetime.fromtimestamp(int(timestamp_ms) / 1000)
                                time_str = timestamp.strftime('%Y-%m-%d %H:%M:%S')

                                # Set start time if not set
                                if not matches[match_id]['start_time']:
                                    matches[match_id]['start_time'] = time_str

                                # Update end time when match completes
                                if game_room.get('stateType') == 'MatchGameRoomStateType_MatchCompleted':
                                    matches[match_id]['end_time'] = time_str

                            # Extract opponent name
                            if not matches[match_id]['opponent_name']:
                                reserved_players = config.get('reservedPlayers', [])
                                # Find the opponent (not the current user)
                                for player in reserved_players:
                                    if player.get('systemSeatId') == 2:  # Assume opponent is seat 2 initially
                                        matches[match_id]['opponent_name'] = player.get('playerName', 'Unknown')
                                        break
                    except (json.JSONDecodeError, KeyError, ValueError):
                        pass

        return list(matches.values())

    @staticmethod
    def parse_basic_log(match_id: str) -> None:
        """Parse basic log information when detailed logging is not enabled"""
        print(f"Parsing logs for match: {match_id[:8]}...")
        print("")
        print("=" * 60)
        print("WARNING: DETAILED LOGGING NOT ENABLED")
        print("=" * 60)
        print("")
        print("To use this parser, you must enable detailed logging in MTG Arena:")
        print("")
        print("1. Launch MTG Arena")
        print("2. Click the gear icon in the top right")
        print("3. Go to 'View Account' (bottom of settings menu)")
        print("4. Enable 'Detailed Logs (Plugin Support)'")
        print("5. Restart MTG Arena")
        print("")