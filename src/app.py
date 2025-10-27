from typing import Dict, Optional

import typer

from src.type_definitions import CardInfo
from src.cards_database.card_database import CardDatabase
from src.formatter.output_formatter import OutputFormatter
from src.helper import Helper
from src.parsers.match_parser import MatchParser
from src.config import Config


app: typer.Typer = typer.Typer()


def parse_match_by_id(log_file: str, match_id: str) -> None:
    """Parse and display a specific match"""
    # Load card database
    card_db: Dict[str, CardInfo] = CardDatabase().load_card_database()
    if card_db:
        print(f"Loaded {len(card_db)} cards from database")
        print("")

    # Check if detailed logging is enabled
    if not Helper.check_detailed_logging_enabled(log_file):
        Helper.parse_basic_log(match_id)
        return

    # Parse the match
    parser: MatchParser = MatchParser(log_file, match_id, card_db)
    player_cards: Dict[int, int]
    opponent_cards: Dict[int, int]
    player_cards, opponent_cards = parser.parse()

    # Display results
    if opponent_cards or player_cards or parser.player_deck:
        OutputFormatter.display_player_deck(player_cards, parser.player_deck, card_db, parser.player_commander)
        OutputFormatter.display_opponent_deck(opponent_cards, parser.opponent_deck_size, card_db, parser.opponent_commander, parser.opponent_name)
    else:
        Helper.parse_basic_log(match_id)


@app.command()
def interactive() -> None:
    """
    Interactive mode: list all matches and let user select one
    """
    config = Config()
    log_file = config.player_log_path

    print("MTG Arena Match Log Parser")
    print("=" * 60)
    print("")

    # Get all match IDs with metadata
    print("Scanning log file for matches...")
    matches = Helper.get_all_match_ids(log_file)

    if not matches:
        print("No matches found in log file")
        return

    print(f"Found {len(matches)} matches")
    print("")

    # Display matches with better formatting
    print(f"{'#':<4} {'Start Time':<20} {'End Time':<20} {'Opponent':<20}")
    print("=" * 70)

    for i, match in enumerate(matches, 1):
        start = match.get('start_time') or 'Unknown'
        end = match.get('end_time') or 'In Progress'
        opponent = match.get('opponent_name') or 'Unknown'
        print(f"{i:<4} {start:<20} {end:<20} {opponent:<20}")

    print("")
    print("=" * 70)

    # Get user selection
    while True:
        try:
            selection = input(f"Select match number (or 'q' to quit) [{len(matches)}]: ").strip()

            # Default to last match if empty
            if not selection:
                selection = str(len(matches))

            if selection.lower() == 'q':
                print("Exiting...")
                return

            match_num = int(selection)
            if 1 <= match_num <= len(matches):
                selected_match = matches[match_num - 1]
                match_id = selected_match['match_id']
                print("")
                print(f"Selected match vs {selected_match.get('opponent_name', 'Unknown')}")
                print(f"Match ID: {match_id}")
                print("")
                parse_match_by_id(log_file, match_id)
                return
            else:
                print(f"Please enter a number between 1 and {len(matches)}")
        except ValueError:
            print("Invalid input. Please enter a number or 'q' to quit")
        except (EOFError, KeyboardInterrupt):
            print("\nExiting...")
            return


@app.command()
def parse_match(log_file: str, match_id: str) -> None:
    """
    Parse match logs and display results (direct mode)
    """
    parse_match_by_id(log_file, match_id)

if __name__ == '__main__':
    app()