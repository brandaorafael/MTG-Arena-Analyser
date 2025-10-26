class Helper:
    """Helper functions"""

    @staticmethod
    def check_detailed_logging_enabled(log_file: str) -> bool:
        """Check if detailed logging is enabled"""
        with open(log_file, 'r') as f:
            first_lines: str = f.read(1000)
            return "DETAILED LOGS: DISABLED" not in first_lines

    @staticmethod
    def parse_basic_log(match_id: str) -> None:
        """Parse basic log information when detailed logging is not enabled"""
        print(f"📖 Parsing logs for match: {match_id[:8]}...")
        print("")
        print("=" * 60)
        print("⚠️  DETAILED LOGGING NOT ENABLED")
        print("=" * 60)
        print("")
        print("To use this parser, you must enable detailed logging in MTG Arena:")
        print("")
        print("1. Launch MTG Arena")
        print("2. Click the gear icon (⚙️) in the top right")
        print("3. Go to 'View Account' (bottom of settings menu)")
        print("4. Enable 'Detailed Logs (Plugin Support)'")
        print("5. Restart MTG Arena")
        print("")