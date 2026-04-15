import logging
from decouple import config

# 🔧 Setup logging
logging.basicConfig(level=logging.INFO)
LOGS = logging.getLogger(__name__)

try:
    # 🔐 Telegram credentials
    APP_ID = config("APP_ID", cast=int)
    API_HASH = config("API_HASH")
    BOT_TOKEN = config("BOT_TOKEN")

    # 👤 Developer & Owner (FIXED TYPES)
    DEV = int(config("DEV", default=0))
    OWNER = list(map(int, config("OWNER", default="").split()))

    # 🎬 Optimized FFmpeg settings (FAST + GOOD QUALITY)
    ffmpegcode = [
        "-c:v libx265 -preset medium -crf 30 "
        "-vf scale=1280:-2 "
        "-c:a aac -b:a 64k "
        "-threads 0"
    ]

    # 🖼 Thumbnail (optional)
    THUMB = config("THUMBNAIL", default=None)

    LOGS.info("✅ Environment variables loaded successfully")

except Exception as e:
    LOGS.error("❌ Environment variables missing or invalid")
    LOGS.error(str(e))
    raise e
