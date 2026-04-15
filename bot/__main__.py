from .config import *

import os, asyncio, time
from pathlib import Path
from telethon import TelegramClient, events, Button
from telethon.errors import FloodWaitError

# ======================
# 🔥 GLOBAL STATE
# ======================
QUEUE = {}
WORKING = False
CANCEL = False

# ======================
# 🚀 BOT START
# ======================
bot = TelegramClient("bot", APP_ID, API_HASH).start(bot_token=BOT_TOKEN)
LOGS.info("🚀 Intelligent Compressor Bot Started")

def auth(uid):
    return uid in OWNER or uid == DEV

# ======================
# 🌐 RENDER KEEP ALIVE
# ======================
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot Running")

def run_server():
    port = int(os.environ.get("PORT", 8000))
    HTTPServer(("0.0.0.0", port), Handler).serve_forever()

threading.Thread(target=run_server, daemon=True).start()

# ======================
# 📊 PROGRESS HANDLER
# ======================
async def progress(current, total, message, start, text):
    now = time.time()
    diff = now - start

    if int(diff) % 10 != 0:
        return

    percent = (current * 100 / total) if total else 0
    bar = "█" * int(percent // 10) + "░" * (10 - int(percent // 10))

    try:
        await message.edit(f"{text}\n\n{bar} {round(percent,2)}%")
    except FloodWaitError as e:
        await asyncio.sleep(e.seconds)
    except:
        pass

# ======================
# 🚀 START COMMAND
# ======================
@bot.on(events.NewMessage(pattern="/start"))
async def start(e):
    if not auth(e.sender_id):
        return await e.reply("❌ Not allowed")
    await e.reply("📥 Send video → I will compress it smartly")

# ======================
# ❌ CANCEL COMMAND
# ======================
@bot.on(events.NewMessage(pattern="/cancel"))
async def cancel(e):
    global CANCEL, QUEUE

    if not auth(e.sender_id):
        return

    CANCEL = True
    QUEUE.clear()
    await e.reply("❌ Cancelled all tasks")

# ======================
# ❌ CANCEL BUTTON
# ======================
@bot.on(events.CallbackQuery(data=b"cancel"))
async def cancel_btn(e):
    global CANCEL, QUEUE

    CANCEL = True
    QUEUE.clear()
    await e.answer("Cancelled", alert=True)

# ======================
# 📥 QUEUE HANDLER (ONLY LAST VIDEO)
# ======================
@bot.on(events.NewMessage(incoming=True))
async def queue_handler(e):
    global QUEUE, CANCEL

    if not auth(e.sender_id):
        return

    if e.video or e.document:
        QUEUE.clear()
        CANCEL = True

        QUEUE[e.id] = e.media
        await e.reply("📥 New video added (old removed)")

# ======================
# 🧠 INTELLIGENT ENGINE
# ======================
def smart_encoder(size_mb):
    if size_mb <= 50:
        return ("libx264", 23, "96k", "fast")
    elif size_mb <= 300:
        return ("libx265", 28, "64k", "medium")
    else:
        return ("libx265", 32, "48k", "slow")

# ======================
# 🚀 WORKER
# ======================
async def worker():
    global WORKING, CANCEL

    while True:
        try:

            if not WORKING and QUEUE:
                WORKING = True
                CANCEL = False

                file_id, file = list(QUEUE.items())[0]
                user = OWNER[0]

                os.makedirs("downloads", exist_ok=True)
                os.makedirs("encode", exist_ok=True)

                msg = await bot.send_message(
                    user,
                    "📥 Starting...",
                    buttons=[[Button.inline("❌ Cancel", b"cancel")]]
                )

                # ======================
                # 📥 DOWNLOAD
                # ======================
                start = time.time()
                dl = f"downloads/{file_id}.mp4"

                await bot.download_media(
                    file,
                    file=dl,
                    progress_callback=lambda d, t: asyncio.create_task(
                        progress(d, t, msg, start, "📥 Downloading")
                    )
                )

                if CANCEL:
                    await msg.edit("❌ Cancelled")
                    WORKING = False
                    continue

                # ======================
                # 🧠 SMART ANALYSIS
                # ======================
                size_mb = Path(dl).stat().st_size / (1024 * 1024)
                codec, crf, audio, preset = smart_encoder(size_mb)

                out = f"encode/{file_id}.mkv"

                # ======================
                # 🗜 COMPRESS
                # ======================
                await msg.edit("🗜 Compressing...")

                cmd = f'''
ffmpeg -y -i "{dl}" 
-vf "scale=-2:720" 
-c:v {codec} -preset {preset} -crf {crf} 
-c:a aac -b:a {audio} 
-movflags +faststart 
"{out}"
'''

                process = await asyncio.create_subprocess_shell(
                    cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )

                await process.communicate()

                if CANCEL:
                    await msg.edit("❌ Cancelled")
                    WORKING = False
                    continue

                if not os.path.exists(out):
                    await msg.edit("❌ Compression failed")
                    WORKING = False
                    continue

                # ======================
                # 📊 STATS
                # ======================
                org = Path(dl).stat().st_size
                com = Path(out).stat().st_size
                saved = 100 - ((com / org) * 100)

                await msg.edit(
                    f"📊 Done\n\n"
                    f"Original: {round(org/1024/1024,2)} MB\n"
                    f"Compressed: {round(com/1024/1024,2)} MB\n"
                    f"Saved: {round(saved,2)}%"
                )

                if CANCEL:
                    WORKING = False
                    continue

                # ======================
                # 📤 UPLOAD
                # ======================
                await bot.send_file(user, out, caption="✅ Compressed Successfully")

                # ======================
                # 🧹 CLEANUP
                # ======================
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

# ======================
# 🚀 RUN BOT
# ======================
with bot:
    bot.loop.run_until_complete(worker())
    bot.loop.run_forever()
