#!/usr/bin/env python3
"""
MTG Arena Detailed Log Parser
Extracts card information from detailed MTGA logs (Legacy version)
"""

import sys
import json
import re
from collections import defaultdict


class LegacyLogParser:
    """Legacy parser for MTG Arena logs (simple version)"""

    def __init__(self, log_path, match_id):
        self.log_path = log_path
        self.match_id = match_id
        self.opponent_cards = set()
        self.player_cards = set()
        self.card_database = {}

    def extract_card_definitions(self, line):
        """Extract card name/ID mappings from log line"""
        if 'grpId' not in line or ('titleId' not in line and 'name' not in line):
            return

        try:
            json_match = re.search(r'\{[^{}]*"grpId"[^{}]*\}', line)
            if json_match:
                card_data = json.loads(json_match.group())
                if 'grpId' in card_data:
                    grp_id = card_data.get('grpId')
                    name = card_data.get('name') or card_data.get('titleId')
                    if name and grp_id:
                        self.card_database[grp_id] = name
        except (json.JSONDecodeError, ValueError):
            pass

    def extract_game_objects(self, line):
        """Extract card ownership from game state messages"""
        if '"gameStateId"' not in line:
            return

        try:
            json_match = re.search(r'\{.*"gameObjects".*\}', line)
            if not json_match:
                return

            state_data = json.loads(json_match.group())

            if 'gameObjects' in state_data:
                for obj in state_data['gameObjects']:
                    if 'grpId' in obj and 'ownerSeatId' in obj:
                        grp_id = obj['grpId']
                        owner = obj['ownerSeatId']

                        # Seat 1 is usually player, Seat 2 is opponent
                        if owner == 2:
                            self.opponent_cards.add(grp_id)
                        elif owner == 1:
                            self.player_cards.add(grp_id)
        except (json.JSONDecodeError, ValueError, KeyError):
            pass

    def parse(self):
        """Main parsing method"""
        print("📖 Parsing detailed logs...")

        try:
            with open(self.log_path, 'r', encoding='utf-8', errors='ignore') as f:
                in_match = False

                for line in f:
                    # Check if we're in the relevant match
                    if self.match_id in line:
                        in_match = True

                    # Extract card definitions
                    self.extract_card_definitions(line)

                    # Extract game state
                    if in_match:
                        self.extract_game_objects(line)

        except FileNotFoundError:
            print(f"❌ Error: Could not find log file at {self.log_path}")
            return False

        return True

    def get_card_names(self, card_ids):
        """Convert card IDs to names"""
        card_names = []
        for grp_id in sorted(card_ids):
            card_name = self.card_database.get(grp_id, f"Unknown Card (ID: {grp_id})")
            card_names.append(card_name)
        return card_names


class LegacyOutputFormatter:
    """Format and display legacy parser results"""

    @staticmethod
    def display_results(parser):
        """Display parsed card information"""
        print("")
        print("=" * 60)
        print("🎴 OPPONENT'S CARDS")
        print("=" * 60)

        if parser.opponent_cards:
            opponent_card_names = parser.get_card_names(parser.opponent_cards)

            if opponent_card_names:
                for i, card in enumerate(sorted(set(opponent_card_names)), 1):
                    print(f"{i:2d}. {card}")
            else:
                print("⚠️  Card IDs found but names not available in this log")
                print("   This usually means detailed logging wasn't fully enabled")
        else:
            LegacyOutputFormatter.display_no_cards_message()

        print("")
        print("=" * 60)

        if parser.player_cards:
            opponent_count = len(parser.opponent_cards)
            player_count = len(parser.player_cards)
            print(f"📊 Stats: {opponent_count} opponent cards, {player_count} your cards")

        print("")

    @staticmethod
    def display_no_cards_message():
        """Display message when no cards are found"""
        print("⚠️  No opponent cards found in this match log")
        print("")
        print("This could mean:")
        print("  1. Detailed logging wasn't enabled during the match")
        print("  2. The match data hasn't been fully written to the log yet")
        print("")
        print("To get full card data:")
        print("  • Enable detailed logging in MTGA settings")
        print("  • Use the enhanced parser: parse_cards_enhanced.py")


def main():
    """Main entry point"""
    if len(sys.argv) < 3:
        print("Usage: parse_cards.py <log_file> <match_id>")
        sys.exit(1)

    log_file = sys.argv[1]
    match_id = sys.argv[2]

    parser = LegacyLogParser(log_file, match_id)
    success = parser.parse()

    if success:
        LegacyOutputFormatter.display_results(parser)


if __name__ == "__main__":
    main()
