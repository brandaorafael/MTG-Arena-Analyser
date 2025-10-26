#!/usr/bin/env python3
"""
Configuration loader for MTG Arena Log Parser
Loads settings from config.yaml
"""

import os
import yaml
from typing import Dict, Any, List


class Config:
    """Configuration manager for the application"""

    _instance = None
    _config: Dict[str, Any] = {}

    def __new__(cls):
        """Singleton pattern to ensure only one config instance"""
        if cls._instance is None:
            cls._instance = super(Config, cls).__new__(cls)
            cls._instance._load_config()
        return cls._instance

    def _load_config(self) -> None:
        """Load configuration from config.yaml"""
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'config.yaml'
        )

        if not os.path.exists(config_path):
            raise FileNotFoundError(
                f"Config file not found at {config_path}. "
                "Please create config.yaml in the project root."
            )

        with open(config_path, 'r') as f:
            self._config = yaml.safe_load(f)

    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Get a config value using dot notation
        Example: config.get('mtga.player_log')
        """
        keys = key_path.split('.')
        value = self._config

        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
                if value is None:
                    return default
            else:
                return default

        return value

    # Convenience properties for commonly used paths
    @property
    def player_log_path(self) -> str:
        """Path to MTGA player log file"""
        return self.get('mtga.player_log')

    @property
    def logs_dir(self) -> str:
        """Directory containing MTGA logs"""
        return self.get('mtga.logs_dir')

    @property
    def card_database_dir(self) -> str:
        """Path to MTGA card database directory"""
        return self.get('mtga.card_database_dir')


# Singleton instance
config = Config()
