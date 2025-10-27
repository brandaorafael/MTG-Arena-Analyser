from typing import Dict

import typer

from src.type_definitions import CardInfo
from src.cards_database.card_database import CardDatabase
from src.formatter.output_formatter import OutputFormatter
from src.helper import Helper
from src.parsers.match_parser import MatchParser
from src.config import Config
from src.ui.interactive_ui import InteractiveUI


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

    # Load card database once at startup
    print("MTG Arena Match Log Parser")
    print("=" * 60)
    print("")
    print("Loading card database...")
    card_db: Dict[str, CardInfo] = CardDatabase().load_card_database()
    if not card_db:
        print("ERROR: Failed to load card database")
        return

    print(f"Loaded {len(card_db)} cards from database")
    print("")

    # Get all matches once
    print("Scanning log file for matches...")
    matches = Helper.get_all_match_ids(log_file)

    if not matches:
        print("No matches found in log file")
        return

    print(f"Found {len(matches)} matches")
    print("")
    input("Press Enter to continue...")

    # Initialize and run the interactive UI
    ui = InteractiveUI(log_file, matches, card_db)
    ui.run()


@app.command()
def parse_match(log_file: str, match_id: str) -> None:
    """
    Parse match logs and display results (direct mode)
    """
    parse_match_by_id(log_file, match_id)

if __name__ == '__main__':
    app()