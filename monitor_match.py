#!/usr/bin/env python3
"""
Real-Time MTG Arena Match Monitor
Watches the Player.log file and extracts card information as matches progress
"""

import sys
import time
import json
import re
import os


class MatchMonitor:
    """Real-time monitor for MTG Arena matches"""

    def __init__(self, log_file, card_db):
        self.log_file = log_file
        self.card_db = card_db
        self.current_match = None
        self.seen_cards = {}

    def follow_log(self):
        """Generator that yields new lines as they're written to the log"""
        with open(self.log_file, 'r') as f:
            # Seek to end of file
            f.seek(0, 2)

            while True:
                line = f.readline()
                if line:
                    yield line
                else:
                    time.sleep(0.1)

    def handle_new_match(self, match_id):
        """Handle detection of a new match"""
        if self.current_match != match_id:
            self.current_match = match_id
            self.seen_cards = {}
            print(f"\n🎮 New Match Started: {match_id[:8]}...")
            print("-" * 60)

    def handle_card_reveal(self, grp_id, owner):
        """Handle a card being revealed"""
        card_key = f"{owner}_{grp_id}"
        if card_key in self.seen_cards:
            return

        self.seen_cards[card_key] = True
        card_info = self.card_db.get(str(grp_id))
        owner_name = "Opponent" if owner == 2 else "You"

        if card_info:
            print(f"  🃏 {owner_name}: {card_info['name']}")
        else:
            print(f"  🃏 {owner_name}: Card ID {grp_id}")

    def handle_cdc_reference(self, cdc_id):
        """Handle CDC instance ID reference"""
        print(f"  📋 CDC #{cdc_id} (instance ID)")

    def handle_state_change(self, old_state, new_state):
        """Handle match state change"""
        if new_state in ['Playing', 'MatchCompleted', 'Disconnected']:
            print(f"  ⚡ Match state: {old_state} → {new_state}")

            if new_state == 'MatchCompleted':
                print(f"\n✅ Match Completed")
                print(f"   Total cards tracked: {len(self.seen_cards)}")
                print("-" * 60)

    def process_line(self, line):
        """Process a single log line"""
        # Check for new match
        match_id_search = re.search(r'matchId ([a-f0-9-]{36})', line)
        if match_id_search:
            self.handle_new_match(match_id_search.group(1))

        if not self.current_match:
            return

        # Look for grpId in game messages
        if 'grpId' in line:
            grp_matches = re.findall(r'"grpId"\s*:\s*(\d+)', line)
            owner_matches = re.findall(r'"ownerSeatId"\s*:\s*(\d+)', line)

            if grp_matches and owner_matches:
                for grp_id_str, owner_str in zip(grp_matches, owner_matches):
                    grp_id = int(grp_id_str)
                    owner = int(owner_str)
                    self.handle_card_reveal(grp_id, owner)

        # CDC references (basic logs)
        elif 'CDC #' in line:
            cdc_match = re.search(r'Card "CDC #(\d+)"', line)
            if cdc_match:
                self.handle_cdc_reference(cdc_match.group(1))

        # Match state changes
        if 'STATE CHANGED' in line:
            state_match = re.search(r'"old":"([^"]+)","new":"([^"]+)"', line)
            if state_match:
                old_state, new_state = state_match.groups()
                self.handle_state_change(old_state, new_state)

    def run(self):
        """Main monitoring loop"""
        try:
            for line in self.follow_log():
                self.process_line(line)
        except KeyboardInterrupt:
            print("\n\n⏹  Monitor stopped")


def load_card_database():
    """Load the extracted card database"""
    db_path = os.path.expanduser("~/Projects/MTGArena/card_database.json")
    if not os.path.exists(db_path):
        return {}

    with open(db_path, 'r') as f:
        return json.load(f)


def main():
    """Main entry point"""
    log_file = os.path.expanduser("~/Library/Logs/Wizards Of The Coast/MTGA/Player.log")

    if not os.path.exists(log_file):
        print("❌ Player.log not found")
        sys.exit(1)

    print("🔍 MTG Arena Real-Time Match Monitor")
    print("=" * 60)
    print("Monitoring: Player.log")
    print("Press Ctrl+C to stop")
    print("=" * 60)
    print("")

    card_db = load_card_database()
    if card_db:
        print(f"✅ Loaded {len(card_db)} cards from database\n")

    monitor = MatchMonitor(log_file, card_db)
    monitor.run()


if __name__ == "__main__":
    main()
