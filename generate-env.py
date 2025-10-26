#!/usr/bin/env python3
"""
Generate .env file for Docker Compose from config.yaml
"""

import yaml
import os

def generate_env():
    """Read config.yaml and generate .env file"""
    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)

    logs_dir = config['mtga']['logs_dir']
    card_db_dir = config['mtga']['card_database_dir']

    env_content = f"""# Auto-generated from config.yaml - DO NOT EDIT MANUALLY
# Run: python3 generate-env.py to regenerate

MTGA_LOGS_DIR={logs_dir}
MTGA_CARD_DB_DIR={card_db_dir}
"""

    with open('.env', 'w') as f:
        f.write(env_content)

    print("✅ Generated .env file from config.yaml")

if __name__ == '__main__':
    generate_env()
