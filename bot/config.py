import logging
from decouple import config

# Setup logging
logging.basicConfig(level=logging.INFO)
LOGS = logging.getLogger(__name__)

try:
    APP_ID = config("APP_ID", cast=int)
    API_HASH = config("API_HASH")
    BOT_TOKEN = config("BOT_TOKEN")

    DEV = config("DEV", default="False")
    OWNER = config("OWNER", default="Unknown")

    # FFmpeg settings
    ffmpegcode = [
        "-preset faster -c:v libx265 -s 854x480 "
        "-x265-params 'bframes=8:psy-rd=1:ref=3:aq-mode=3:aq-strength=0.8:deblock=1,1' "
        "-metadata 'title=Encoded By Bot' "
        "-pix_fmt yuv420p -crf 30 -c:a libopus -b:a 32k "
        "-c:s copy -map 0 -ac 2 -ab 32k -vbr 2 -level 3.1 -threads 1"
    ]

    # Make thumbnail optional ✅
    THUMB = config("THUMBNAIL", default=None)

    LOGS.info("✅ Environment variables loaded successfully")

except Exception as e:
    LOGS.error("❌ Environment variables missing or invalid")
    LOGS.error(str(e))
    raise e  # Better than exit(1)
