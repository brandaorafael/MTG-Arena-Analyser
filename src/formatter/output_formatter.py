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
                card_list.append((name, count))
        return sorted(card_list)

    @staticmethod
    def format_card_list_by_type(cards, card_db):
        """Format cards grouped by type"""
        # Group cards by their primary type
        type_groups = {
            'Creature': [],
            'Planeswalker': [],
            'Artifact': [],
            'Enchantment': [],
            'Instant': [],
            'Sorcery': [],
            'Land': [],
            'Other': []
        }

        for grp_id, count in cards.items():
            card_info = card_db.get(str(grp_id))
            if card_info:
                name = card_info['name']
                types = card_info.get('types', [])

                # Determine primary type (first type in list)
                primary_type = types[0] if types else 'Other'

                # If type not in our predefined groups, put in Other
                if primary_type not in type_groups:
                    primary_type = 'Other'

                type_groups[primary_type].append((name, count))

        # Sort cards within each group
        for type_name in type_groups:
            type_groups[type_name].sort()

        return type_groups

    @staticmethod
    def print_card_list(card_list):
        """Print a formatted card list"""
        for i, (name, count) in enumerate(card_list, 1):
            if count > 1:
                print(f"  {i:2d}. {name} (x{count})")
            else:
                print(f"  {i:2d}. {name}")

    @staticmethod
    def print_grouped_card_list(type_groups):
        """Print cards grouped by type"""
        # Define display order and plural forms
        type_display = {
            'Creature': 'Creatures',
            'Planeswalker': 'Planeswalkers',
            'Instant': 'Instants',
            'Sorcery': 'Sorceries',
            'Artifact': 'Artifacts',
            'Enchantment': 'Enchantments',
            'Land': 'Lands',
            'Other': 'Other'
        }

        for type_name, plural_name in type_display.items():
            cards = type_groups.get(type_name, [])
            if cards:
                # Count total cards in this group (counting duplicates)
                total_in_group = sum(count for name, count in cards)
                print(f"\n  {plural_name} ({total_in_group}):")
                for name, count in cards:
                    if count > 1:
                        print(f"    • {name} (x{count})")
                    else:
                        print(f"    • {name}")

    @staticmethod
    def display_player_deck(player_cards, player_deck, card_db, commander=None):
        """Display player's deck information"""
        print("")
        print("=" * 60)
        print("🃏 YOUR DECK")
        print("=" * 60)
        print("")

        if player_deck:
            total_cards = sum(player_deck.values())
            # Add commander to total if present (Commander format)
            if commander:
                total_cards += 1
            revealed_count = sum(player_cards.values())

            print("📦 REVEALED CARDS:")

            if player_cards:
                type_groups = OutputFormatter.format_card_list_by_type(player_cards, card_db)
                OutputFormatter.print_grouped_card_list(type_groups)
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
    def display_opponent_deck(opponent_cards, opponent_deck_size, card_db, commander=None):
        """Display opponent's deck information"""
        print("")
        print("=" * 60)
        print("🎴 OPPONENT'S DECK")
        print("=" * 60)
        print("")

        if opponent_cards:
            print("📦 REVEALED CARDS:")

            type_groups = OutputFormatter.format_card_list_by_type(opponent_cards, card_db)
            OutputFormatter.print_grouped_card_list(type_groups)

            print("")
            revealed_count = sum(opponent_cards.values())
            unique_count = len(opponent_cards)

            # Show revealed stats without total (opponent's full deck is hidden)
            print(f"📊 Revealed: {unique_count} unique cards | {revealed_count} total cards")

            if commander:
                card_name = card_db.get(str(commander), {}).get('name', 'Unknown')
                print(f"👑 Commander detected: {card_name}")
        else:
            if opponent_deck_size > 0:
                print(f"No cards revealed (opponent has {opponent_deck_size} cards in deck)")
            else:
                print("No opponent cards found")

        print("")
        print("=" * 60)