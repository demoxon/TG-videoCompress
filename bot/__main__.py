from .config import *

import os, asyncio, time
from pathlib import Path
from telethon import TelegramClient, events, Button

# =========================
# 🔥 GLOBAL STATE
# =========================
USER_SETTINGS = {}
QUEUE = {}
WORKING = False
CANCEL = False

bot = TelegramClient("bot", APP_ID, API_HASH).start(bot_token=BOT_TOKEN)
LOGS.info("🎬 UI Video Editor Bot Started")

def auth(uid):
    return uid in OWNER or uid == DEV

# =========================
# 🌐 RENDER KEEP ALIVE
# =========================
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"UI Bot Running")

def run_server():
    port = int(os.environ.get("PORT", 8000))
    HTTPServer(("0.0.0.0", port), Handler).serve_forever()

threading.Thread(target=run_server, daemon=True).start()

# =========================
# ⚙ DEFAULT SETTINGS
# =========================
DEFAULT = {
    "preset": "balanced",
    "resolution": 360,
    "crf": 30,
    "codec": "libx264"
}

# =========================
# 🎛 UI MENU
# =========================
def main_menu():
    return [
        [Button.inline("🎬 Compress Video", b"compress")],
        [Button.inline("⚙ Settings", b"settings")],
        [Button.inline("❌ Cancel Task", b"cancel")]
    ]

def settings_menu():
    return [
        [Button.inline("🎛 Preset", b"preset")],
        [Button.inline("📐 Resolution", b"res")],
        [Button.inline("🔙 Back", b"back")]
    ]

def preset_menu():
    return [
        [Button.inline("⚡ Fast (Low Size)", b"p_fast")],
        [Button.inline("⚖ Balanced", b"p_bal")],
        [Button.inline("🎥 Quality", b"p_qual")],
        [Button.inline("🔙 Back", b"settings")]
    ]

def res_menu():
    return [
        [Button.inline("240p", b"r240")],
        [Button.inline("360p", b"r360")],
        [Button.inline("720p", b"r720")],
        [Button.inline("🔙 Back", b"settings")]
    ]

# =========================
# 🚀 START
# =========================
@bot.on(events.NewMessage(pattern="/start"))
async def start(e):
    if not auth(e.sender_id):
        return await e.reply("❌ Not allowed")

    USER_SETTINGS[e.sender_id] = DEFAULT.copy()

    await e.reply(
        "🎬 Welcome to Video Editor Bot",
        buttons=main_menu()
    )

# =========================
# 🎛 CALLBACK HANDLER
# =========================
@bot.on(events.CallbackQuery())
async def callback(e):
    global USER_SETTINGS, CANCEL

    uid = e.sender_id

    if uid not in USER_SETTINGS:
        USER_SETTINGS[uid] = DEFAULT.copy()

    data = e.data.decode()

    # ---------------- UI ----------------
    if data == "compress":
        await e.edit("📥 Send your video now")

    elif data == "settings":
        await e.edit("⚙ Settings Panel", buttons=settings_menu())

    elif data == "preset":
        await e.edit("🎛 Choose Preset", buttons=preset_menu())

    elif data == "res":
        await e.edit("📐 Select Resolution", buttons=res_menu())

    elif data == "back":
        await e.edit("🎬 Main Menu", buttons=main_menu())

    # ---------------- PRESETS ----------------
    elif data == "p_fast":
        USER_SETTINGS[uid]["preset"] = "fast"
        USER_SETTINGS[uid]["crf"] = 35
        await e.answer("Fast mode ON")

    elif data == "p_bal":
        USER_SETTINGS[uid]["preset"] = "balanced"
        USER_SETTINGS[uid]["crf"] = 30
        await e.answer("Balanced mode ON")

    elif data == "p_qual":
        USER_SETTINGS[uid]["preset"] = "quality"
        USER_SETTINGS[uid]["crf"] = 26
        await e.answer("Quality mode ON")

    # ---------------- RESOLUTION ----------------
    elif data == "r240":
        USER_SETTINGS[uid]["resolution"] = 240
        await e.answer("240p selected")

    elif data == "r360":
        USER_SETTINGS[uid]["resolution"] = 360
        await e.answer("360p selected")

    elif data == "r720":
        USER_SETTINGS[uid]["resolution"] = 720
        await e.answer("720p selected")

    # ---------------- CANCEL ----------------
    elif data == "cancel":
        CANCEL = True
        QUEUE.clear()
        await e.answer("Cancelled ❌", alert=True)

# =========================
# 📥 VIDEO HANDLER
# =========================
@bot.on(events.NewMessage(incoming=True))
async def video_handler(e):
    global QUEUE, CANCEL

    if not auth(e.sender_id):
        return

    if e.video or e.document:
        QUEUE.clear()
        CANCEL = True

        QUEUE[e.id] = e.media
        await e.reply("📥 Video received. Processing soon...")

# =========================
# 🧠 WORKER
# =========================
async def worker():
    global WORKING, CANCEL

    while True:
        try:
            if QUEUE and not WORKING:
                WORKING = True
                CANCEL = False

                file_id, file = list(QUEUE.items())[0]
                user = OWNER[0]

                settings = USER_SETTINGS.get(user, DEFAULT)

                os.makedirs("downloads", exist_ok=True)
                os.makedirs("encode", exist_ok=True)

                msg = await bot.send_message(user, "📥 Downloading...")

                # ---------------- DOWNLOAD ----------------
                dl = f"downloads/{file_id}.mp4"

                await bot.download_media(file, file=dl)

                if CANCEL:
                    await msg.edit("❌ Cancelled")
                    WORKING = False
                    continue

                # ---------------- SETTINGS ----------------
                res = settings["resolution"]
                crf = settings["crf"]

                out = f"encode/{file_id}.mkv"

                await msg.edit("🗜 Compressing...")

                # ---------------- FFmpeg ----------------
                cmd = f'''
ffmpeg -y -i "{dl}" 
-vf "scale=-2:{res}" 
-c:v libx264 -crf {crf} -pix_fmt yuv420p 
-c:a aac -b:a 64k 
"{out}"
'''

                process = await asyncio.create_subprocess_shell(cmd)
                await process.communicate()

                if CANCEL:
                    WORKING = False
                    continue

                if not os.path.exists(out):
                    await msg.edit("❌ Compression failed")
                    WORKING = False
                    continue

                # ---------------- STATS ----------------
                org = Path(dl).stat().st_size
                com = Path(out).stat().st_size

                await msg.edit(
                    f"📊 Done\n\n"
                    f"Original: {round(org/1024/1024,2)} MB\n"
                    f"Compressed: {round(com/1024/1024,2)} MB"
                )

                # ---------------- UPLOAD ----------------
                await bot.send_file(user, out, caption="🎬 Edited Video")

                # ---------------- CLEAN ----------------
                QUEUE.pop(file_id)
                WORKING = False

                os.remove(dl)
                os.remove(out)

            else:
                await asyncio.sleep(3)

        except Exception as e:
            LOGS.error(e)
            WORKING = False

# =========================
# 🚀 RUN
# =========================
with bot:
    bot.loop.run_until_complete(worker())
    bot.loop.run_forever()
