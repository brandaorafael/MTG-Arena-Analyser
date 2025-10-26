#!/usr/bin/env python3
"""
Extract MTG Arena Card Database
Creates a JSON mapping of card IDs to card names
"""

import sqlite3
import json
import os
import glob


class CardDatabaseExtractor:
    """Extracts card data from MTG Arena's SQLite database"""

    def __init__(self):
        self.mtga_path = os.path.expanduser(
            "~/Library/Application Support/com.wizards.mtga/Downloads/Raw/"
        )
        self.output_path = os.path.expanduser("~/Projects/MTGArena/card_database.json")

    def find_database(self):
        """Find the Raw_CardDatabase file"""
        pattern = os.path.join(self.mtga_path, "Raw_CardDatabase_*.mtga")
        files = glob.glob(pattern)

        if files:
            return files[0]
        return None

    def decode_types(self, types_value):
        """Decode card types from comma-separated type IDs"""
        # MTG card type IDs
        type_map = {
            1: "Artifact",
            2: "Creature",
            3: "Enchantment",
            4: "Instant",
            5: "Land",
            8: "Planeswalker",
            10: "Sorcery",
            # Add more if discovered
        }

        types = []

        if not types_value:
            return types

        # Convert to string for splitting
        types_str = str(types_value)

        # Split by comma for multi-type cards
        type_ids = types_str.split(',')

        for type_id_str in type_ids:
            try:
                type_id = int(type_id_str.strip())
                if type_id in type_map:
                    types.append(type_map[type_id])
            except ValueError:
                continue

        return types

    def extract_cards(self, db_path):
        """Extract all cards with their names and types from the database"""
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        query = """
        SELECT c.GrpId, l.Loc, c.ExpansionCode, c.CollectorNumber, c.Types
        FROM Cards c
        JOIN Localizations_enUS l ON c.TitleId = l.LocId
        WHERE c.IsToken = 0
        ORDER BY c.GrpId
        """

        cursor.execute(query)
        cards = {}

        for row in cursor.fetchall():
            grp_id, name, expansion, collector_num, types_value = row

            # Decode card types
            types = self.decode_types(types_value) if types_value else []

            cards[grp_id] = {
                "name": name,
                "expansion": expansion,
                "collector_number": collector_num,
                "types": types
            }

        conn.close()
        return cards

    def save_to_json(self, cards):
        """Save card data to JSON file"""
        with open(self.output_path, 'w') as f:
            json.dump(cards, f, indent=2)

    def display_sample(self, cards, count=5):
        """Display a sample of extracted cards"""
        print("")
        print("Sample cards:")
        for grp_id in list(cards.keys())[:count]:
            card = cards[grp_id]
            types_str = ", ".join(card['types']) if card['types'] else "Unknown"
            print(f"  {grp_id}: {card['name']} ({types_str})")

    def extract(self):
        """Main extraction process"""
        print("🔍 Finding MTG Arena card database...")

        db_path = self.find_database()
        if not db_path:
            print("❌ Card database not found!")
            print(f"Expected location: {self.mtga_path}")
            return False

        print(f"✅ Found database: {os.path.basename(db_path)}")
        print("📊 Extracting card data...")

        cards = self.extract_cards(db_path)
        print(f"✅ Extracted {len(cards)} cards")

        self.save_to_json(cards)
        print(f"💾 Saved to: {self.output_path}")

        self.display_sample(cards)

        return True


def main():
    """Main entry point"""
    extractor = CardDatabaseExtractor()
    success = extractor.extract()

    if not success:
        exit(1)


if __name__ == "__main__":
    main()
