import logging
from decouple import config

logging.basicConfig(level=logging.INFO)
LOGS = logging.getLogger(__name__)

try:
    APP_ID = config("APP_ID", cast=int)
    API_HASH = config("API_HASH")
    BOT_TOKEN = config("BOT_TOKEN")

    DEV = int(config("DEV", default=0))
    OWNER = list(map(int, config("OWNER", default="").split()))

    # ⚡ Fast compression
    ffmpegcode = [
        "-c:v libx264 -preset ultrafast -crf 28 "
        "-vf scale=1280:-2 "
        "-c:a aac -b:a 96k "
        "-threads 0"
    ]

    THUMB = config("THUMBNAIL", default=None)

    LOGS.info("✅ Config Loaded")

except Exception as e:
    LOGS.error(str(e))
    raise e
