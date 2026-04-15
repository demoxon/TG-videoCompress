from .config import *

import os, asyncio, time
from pathlib import Path
from telethon import TelegramClient, events, Button
from telethon.errors import FloodWaitError

# 🔥 GLOBALS
QUEUE = {}
WORKING = False
CANCEL = False

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

# 📊 PROGRESS
async def progress(current, total, message, start, text):
    now = time.time()
    diff = now - start

    if int(diff) % 10 != 0:
        return

    percent = current * 100 / total if total else 0
    bar = "█" * int(percent // 10) + "░" * (10 - int(percent // 10))

    try:
        await message.edit(f"{text}\n\n{bar} {round(percent,2)}%")
    except FloodWaitError as e:
        await asyncio.sleep(e.seconds)
    except:
        pass

# ✅ START
@bot.on(events.NewMessage(pattern="/start"))
async def start(e):
    if not auth(e.sender_id):
        return await e.reply("❌ Not allowed")
    await e.reply("✅ Send video to compress")

# ❌ CANCEL COMMAND
@bot.on(events.NewMessage(pattern="/cancel"))
async def cancel_cmd(e):
    global CANCEL, QUEUE

    if not auth(e.sender_id):
        return

    CANCEL = True
    QUEUE.clear()
    await e.reply("❌ Cancelled")

# ❌ CANCEL BUTTON
@bot.on(events.CallbackQuery(data=b"cancel"))
async def cancel_btn(e):
    global CANCEL, QUEUE

    CANCEL = True
    QUEUE.clear()
    await e.answer("Cancelled", alert=True)

# 📥 ADD TO QUEUE (ONLY LATEST)
@bot.on(events.NewMessage(incoming=True))
async def add_queue(e):
    global QUEUE, CANCEL

    if not auth(e.sender_id):
        return

    if e.video or e.document:
        QUEUE.clear()
        CANCEL = True

        QUEUE[e.id] = e.media
        await e.reply("📥 Added (old task removed)")

# 🚀 WORKER
async def worker():
    global WORKING, CANCEL

    while True:
        try:
            if not WORKING and QUEUE:
                WORKING = True
                CANCEL = False

                file_id, file = list(QUEUE.items())[0]
                user = OWNER[0]

                # 📁 Ensure folders exist
                os.makedirs("downloads", exist_ok=True)
                os.makedirs("encode", exist_ok=True)

                # 📩 SINGLE MESSAGE
                try:
                    msg = await bot.send_message(
                        user,
                        "📥 Starting...",
                        buttons=[[Button.inline("❌ Cancel", b"cancel")]]
                    )
                except FloodWaitError as e:
                    await asyncio.sleep(e.seconds)

                # 📥 DOWNLOAD
                start = time.time()
                dl = f"downloads/{file_id}.mp4"

                await bot.download_media(
                    file,
                    file=dl,
                    progress_callback=lambda d, t: asyncio.create_task(
                        progress(d, t, msg, start, "📥 Downloading...")
                    )
                )

                if CANCEL:
                    await msg.edit("❌ Cancelled")
                    WORKING = False
                    continue

                # 🎬 COMPRESS (SAFE)
                out = f"encode/{file_id}.mkv"

                await msg.edit("🗜 Compressing...")

                cmd = f'ffmpeg -y -i "{dl}" -c:v libx264 -preset ultrafast -crf 28 -vf "scale=-2:720" -c:a aac -b:a 96k "{out}"'

                process = await asyncio.create_subprocess_shell(
                    cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )

                stdout, stderr = await process.communicate()

                if CANCEL:
                    process.kill()
                    await msg.edit("❌ Cancelled")
                    WORKING = False
                    continue

                if process.returncode != 0:
                    await msg.edit(f"❌ Compression failed\n\n{stderr.decode()[:300]}")
                    WORKING = False
                    QUEUE.clear()
                    continue

                # 🛑 Check file exists
                if not os.path.exists(out):
                    await msg.edit("❌ Output file not created")
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

                if CANCEL:
                    WORKING = False
                    continue

                # 📤 UPLOAD
                try:
                    await bot.send_file(user, out, caption="✅ Done")
                except FloodWaitError as e:
                    await asyncio.sleep(e.seconds)
                    await bot.send_file(user, out, caption="✅ Done")

                # 🧹 CLEANUP
                QUEUE.pop(file_id)
                WORKING = False

                if os.path.exists(dl):
                    os.remove(dl)
                if os.path.exists(out):
                    os.remove(out)

            else:
                await asyncio.sleep(3)

        except FloodWaitError as e:
            await asyncio.sleep(e.seconds)

        except Exception as e:
            LOGS.error(e)
            WORKING = False

# 🚀 RUN
with bot:
    bot.loop.run_until_complete(worker())
    bot.loop.run_forever()
