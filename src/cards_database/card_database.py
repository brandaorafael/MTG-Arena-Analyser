#!/usr/bin/env python3
"""
Extract MTG Arena Card Database
Creates a JSON mapping of card IDs to card names
"""

import sqlite3
import json
import os
import glob
from typing import Dict, List, Optional, Any


class CardDatabase:
    """Extracts and loads card data from MTG Arena's SQLite database"""

    def __init__(self) -> None:
        self.mtga_path: str = os.path.expanduser(
            "/Users/rafael.brandao/Library/Application Support/com.wizards.mtga/Downloads/Raw/"
        )
        self.output_path: str = os.path.expanduser("./src/cards_database/card_database.json")

    def _find_database(self) -> Optional[str]:
        """Find the Raw_CardDatabase file"""
        pattern: str = os.path.join(self.mtga_path, "Raw_CardDatabase_*.mtga")
        files: List[str] = glob.glob(pattern)

        if files:
            return files[0]
        return None

    def _decode_types(self, types_value: Any) -> List[str]:
        """Decode card types from comma-separated type IDs"""
        # MTG card type IDs
        type_map: Dict[int, str] = {
            1: "Artifact",
            2: "Creature",
            3: "Enchantment",
            4: "Instant",
            5: "Land",
            8: "Planeswalker",
            10: "Sorcery",
            # Add more if discovered
        }

        types: List[str] = []

        if not types_value:
            return types

        # Convert to string for splitting
        types_str: str = str(types_value)

        # Split by comma for multi-type cards
        type_ids: List[str] = types_str.split(',')

        for type_id_str in type_ids:
            try:
                type_id: int = int(type_id_str.strip())
                if type_id in type_map:
                    types.append(type_map[type_id])
            except ValueError:
                continue

        return types

    def _extract_cards(self, db_path: str) -> Dict[int, Dict[str, Any]]:
        """Extract all cards with their names and types from the database"""
        conn: sqlite3.Connection = sqlite3.connect(db_path)
        cursor: sqlite3.Cursor = conn.cursor()

        query: str = """
        SELECT c.GrpId, l.Loc, c.ExpansionCode, c.CollectorNumber, c.Types
        FROM Cards c
        JOIN Localizations_enUS l ON c.TitleId = l.LocId
        WHERE c.IsToken = 0
        ORDER BY c.GrpId
        """

        cursor.execute(query)
        cards: Dict[int, Dict[str, Any]] = {}

        for row in cursor.fetchall():
            grp_id, name, expansion, collector_num, types_value = row

            # Decode card types
            types: List[str] = self._decode_types(types_value) if types_value else []

            cards[grp_id] = {
                "name": name,
                "expansion": expansion,
                "collector_number": collector_num,
                "types": types
            }

        conn.close()
        return cards

    def _save_to_json(self, cards: Dict[int, Dict[str, Any]]) -> None:
        """Save card data to a JSON file"""
        with open(self.output_path, 'w') as f:
            json.dump(cards, f, indent=2)

    def _display_sample(self, cards: Dict[int, Dict[str, Any]], count: int = 5) -> None:
        """Display a sample of extracted cards"""
        print("")
        print("Sample cards:")
        for grp_id in list(cards.keys())[:count]:
            card: Dict[str, Any] = cards[grp_id]
            types_str: str = ", ".join(card['types']) if card['types'] else "Unknown"
            print(f"  {grp_id}: {card['name']} ({types_str})")

    def extract(self) -> bool:
        """Main extraction process"""
        print("🔍 Finding MTG Arena card database...")

        db_path: Optional[str] = self._find_database()
        if not db_path:
            print("❌ Card database not found!")
            print(f"Expected location: {self.mtga_path}")
            return False

        print(f"✅ Found database: {os.path.basename(db_path)}")
        print("📊 Extracting card data...")

        cards: Dict[int, Dict[str, Any]] = self._extract_cards(db_path)
        print(f"✅ Extracted {len(cards)} cards")

        self._save_to_json(cards)
        print(f"💾 Saved to: {self.output_path}")

        self._display_sample(cards)

        return True

    def load_card_database(self) -> Dict[str, Dict[str, Any]]:
        """Load the extracted card database"""
        path: str = "./src/cards_database/card_database.json"

        db_path: str = os.path.expanduser(path)
        if not os.path.exists(db_path):
            print("⚠️  Card database not found.")

            extractor: CardDatabase = CardDatabase()
            success: bool = extractor.extract()

            if not success:
                exit(1)

            db_path = os.path.expanduser(path)
            if not os.path.exists(db_path):
                print("⚠️  Failed importing Cards.")
                return {}

        with open(db_path, 'r') as f:
            return json.load(f)
