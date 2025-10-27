"""Interactive UI for match selection and display"""

import os
from typing import Dict, List, Optional
from simple_term_menu import TerminalMenu

from src.type_definitions import CardInfo
from src.formatter.output_formatter import OutputFormatter
from src.helper import Helper
from src.parsers.match_parser import MatchParser


class InteractiveUI:
    """Handles interactive terminal UI for match selection"""

    def __init__(self, log_file: str, matches: List[Dict[str, Optional[str]]], card_db: Dict[str, CardInfo]):
        """
        Initialize the interactive UI

        Args:
            log_file: Path to the MTGA log file
            matches: List of match dictionaries with metadata
            card_db: Card database dictionary
        """
        self.log_file = log_file
        self.matches = matches
        self.card_db = card_db
        self.last_cursor_index = len(matches) - 1  # Start at most recent

    def _clear_screen(self) -> None:
        """Clear the terminal screen"""
        os.system('clear' if os.name != 'nt' else 'cls')

    def _show_match_menu(self) -> Optional[int]:
        """
        Display the interactive match selection menu

        Returns:
            Selected match index, or None if user quit
        """
        self._clear_screen()

        # Build menu options
        menu_items = []
        for i, match in enumerate(self.matches, 1):
            start = match.get('start_time') or 'Unknown'
            end = match.get('end_time') or 'In Progress'
            opponent = match.get('opponent_name') or 'Unknown'

            # Format each line to be aligned
            menu_item = f"{i:<4} {start:<20} {end:<20} {opponent:<20}"
            menu_items.append(menu_item)

        # Show header
        print("MTG Arena Match Log Parser")
        print("")
        print("Use arrow keys to navigate, Enter to select, q to quit")
        print("")
        print("=" * 70)
        print(f"  {'#':<4} {'Start Time':<20} {'End Time':<20} {'Opponent':<20}")
        print("=" * 70)

        # Create interactive menu
        terminal_menu = TerminalMenu(
            menu_items,
            title=None,
            cursor_index=self.last_cursor_index,
            menu_cursor="> ",
            menu_cursor_style=("fg_green", "bold"),
            menu_highlight_style=("bg_green", "fg_black"),
            cycle_cursor=True,
            clear_screen=False,
        )

        # Show menu and get selection
        selected_index = terminal_menu.show()

        # Update cursor position for next time
        if selected_index is not None:
            self.last_cursor_index = selected_index

        return selected_index

    def _display_match_results(self, match_index: int) -> None:
        """
        Parse and display results for the selected match

        Args:
            match_index: Index of the selected match
        """
        self._clear_screen()

        # Get selected match info
        selected_match = self.matches[match_index]
        match_id = selected_match['match_id']

        # Show header
        print("MTG Arena Match Log Parser")
        print("=" * 60)
        print("")
        print(f"Selected match vs {selected_match.get('opponent_name', 'Unknown')}")
        print(f"Match ID: {match_id}")
        print("")

        # Check if detailed logging is enabled
        if not Helper.check_detailed_logging_enabled(self.log_file):
            Helper.parse_basic_log(match_id)
        else:
            # Parse the match
            parser: MatchParser = MatchParser(self.log_file, match_id, self.card_db)
            player_cards: Dict[int, int]
            opponent_cards: Dict[int, int]
            player_cards, opponent_cards = parser.parse()

            # Display results
            if opponent_cards or player_cards or parser.player_deck:
                OutputFormatter.display_player_deck(
                    player_cards,
                    parser.player_deck,
                    self.card_db,
                    parser.player_commander
                )
                OutputFormatter.display_opponent_deck(
                    opponent_cards,
                    parser.opponent_deck_size,
                    self.card_db,
                    parser.opponent_commander,
                    parser.opponent_name
                )
            else:
                Helper.parse_basic_log(match_id)

    def run(self) -> None:
        """
        Run the interactive UI loop

        Continues until user quits with 'q' or Esc
        """
        while True:
            # Show menu and get selection
            selected_index = self._show_match_menu()

            # Handle cancellation (Esc or q)
            if selected_index is None:
                self._clear_screen()
                print("Exiting...")
                return

            # Display match results
            self._display_match_results(selected_index)

            # Wait for user to press Enter to go back to menu
            print("")
            input("Press Enter to return to match selection...")
