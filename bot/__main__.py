from .config import *

import os
import asyncio
import time
from pathlib import Path
from telethon import TelegramClient, events

# 🔥 GLOBALS
QUEUE = {}
WORKING = False

# 🚀 START BOT
bot = TelegramClient("bot", APP_ID, API_HASH).start(bot_token=BOT_TOKEN)
LOGS.info("🚀 Bot Started")

# 🔐 AUTH
def auth(uid):
    return uid in OWNER or uid == DEV

# 🌐 RENDER PORT FIX
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot running")

def run_server():
    port = int(os.environ.get("PORT", 8000))
    server = HTTPServer(("0.0.0.0", port), Handler)
    server.serve_forever()

threading.Thread(target=run_server, daemon=True).start()

# ✅ PROGRESS FUNCTION (NO SPAM)
async def progress(current, total, message, start, text):
    now = time.time()
    diff = now - start

    if round(diff % 5) != 0:
        return

    percentage = current * 100 / total if total else 0
    speed = current / diff if diff > 0 else 0
    remaining = round((total - current) / speed) if speed > 0 else 0

    bar_length = 10
    filled = int(bar_length * current // total) if total else 0
    bar = "█" * filled + "░" * (bar_length - filled)

    msg = (
        f"{text}\n\n"
        f"{bar} {round(percentage,2)}%\n\n"
        f"⚡ Speed: {round(speed/1024,2)} KB/s\n"
        f"⏱ ETA: {remaining}s"
    )

    try:
        await message.edit(msg)
    except:
        pass

# ✅ START COMMAND
@bot.on(events.NewMessage(pattern="/start"))
async def start_cmd(e):
    if not auth(e.sender_id):
        return await e.reply("❌ Not allowed")
    await e.reply("✅ Send a video to compress")

# 📥 ADD TO QUEUE
@bot.on(events.NewMessage(incoming=True))
async def add_queue(e):
    if not auth(e.sender_id):
        return

    if e.video or e.document:
        QUEUE[e.id] = e.media
        await e.reply("📥 Added to queue")

# 🚀 WORKER
async def worker():
    global WORKING

    while True:
        try:
            if not WORKING and QUEUE:
                WORKING = True

                file_id, file = list(QUEUE.items())[0]
                user = OWNER[0]

                msg = await bot.send_message(user, "📥 Starting download...")

                # 📥 DOWNLOAD (STABLE)
                start = time.time()
                dl = f"downloads/{file_id}.mp4"

                await bot.download_media(
                    file,
                    file=dl,
                    progress_callback=lambda d, t: asyncio.create_task(
                        progress(d, t, msg, start, "📥 Downloading...")
                    )
                )

                size = Path(dl).stat().st_size / (1024 * 1024)

                # 🎯 SMART COMPRESSION
                if size > 300:
                    code = "-c:v libx264 -preset ultrafast -crf 30 -vf scale=854:-2 -c:a aac -b:a 96k -threads 0"
                else:
                    code = ffmpegcode[0]

                out = f"encode/{file_id}.mkv"

                await msg.edit("🗜 Compressing...")

                cmd = f'ffmpeg -i "{dl}" {code} "{out}" -y'

                process = await asyncio.create_subprocess_shell(cmd)
                await process.communicate()

                if process.returncode != 0:
                    await msg.edit("❌ Compression failed")
                    QUEUE.pop(file_id)
                    WORKING = False
                    continue

                # 📊 STATS
                org = Path(dl).stat().st_size
                com = Path(out).stat().st_size
                per = 100 - ((com / org) * 100)

                await msg.edit(
                    f"📊 Done\n\n"
                    f"Original: {round(org/1024/1024,2)} MB\n"
                    f"Compressed: {round(com/1024/1024,2)} MB\n"
                    f"Saved: {round(per,2)}%"
                )

                # 📤 UPLOAD (STABLE)
                await bot.send_file(
                    user,
                    out,
                    caption="✅ Compressed successfully"
                )

                # 🧹 CLEANUP
                QUEUE.pop(file_id)
                WORKING = False

                if os.path.exists(dl):
                    os.remove(dl)
                if os.path.exists(out):
                    os.remove(out)

            else:
                await asyncio.sleep(3)

        except Exception as e:
            LOGS.error(e)
            WORKING = False

# 🚀 RUN
with bot:
    bot.loop.run_until_complete(worker())
    bot.loop.run_forever()
