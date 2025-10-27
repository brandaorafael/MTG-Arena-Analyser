from typing import Dict

import typer

from src.type_definitions import CardInfo

# # Add parent folder to the python path to be able to access "/components" and "/shared"
# parentdir = Path(__file__).resolve().parents[1].parents[0]
# sys.path.insert(0, str(parentdir))

from src.cards_database.card_database import CardDatabase
from src.formatter.output_formatter import OutputFormatter
from src.helper import Helper
from src.parsers.match_parser import MatchParser


app: typer.Typer = typer.Typer()


@app.command()
def kk() -> None:
    pass

@app.command()
def parse_match(log_file: str, match_id: str) -> None:
    """
    PArse match logs and display results

    :return: None
    """

    # Load card database
    card_db: Dict[str, CardInfo] = CardDatabase().load_card_database()
    if card_db:
        print(f"✅ Loaded {len(card_db)} cards from database")
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

if __name__ == '__main__':
    app()