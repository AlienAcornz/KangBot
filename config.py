import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()
TOKEN: str = os.getenv('DISCORD_TOKEN') or ''
if not TOKEN:
    raise ValueError('DISCORD_TOKEN environment variable is required')

BUILD_TYPE: str = os.getenv('BUILD_TYPE') or ''
if not BUILD_TYPE:
    raise ValueError('BUILD_TYPE environment variable is required')

DEV_GUILD_ID: str = os.getenv('DEVELOPMENT_GUILD_ID') or ''
if not DEV_GUILD_ID:
    raise ValueError('BUILD_TYPE environment variable is required')

BASE_DIR = Path(__file__).resolve().parent

DB_PATH = BASE_DIR / "data" / "moderation.db"