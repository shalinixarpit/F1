from os import getenv

API_ID = int(getenv("API_ID", ""))
API_HASH = getenv("API_HASH", "")
BOT_TOKEN = getenv("BOT_TOKEN", "")
SESSION = getenv("SESSION", "")

LOG_CHANNEL = getenv("LOG_CHANNEL", "")
DEST_CHANNEL = getenv("DEST_CHANNEL", "")
