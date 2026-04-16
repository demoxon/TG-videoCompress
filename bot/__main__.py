from .config import *

import os, asyncio, time
from pathlib import Path
from telethon import events, Button, TelegramClient
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading

# =========================
# 🔥 STATE
# =========================
USER_SETTINGS = {}
QUEUE = {}          # per-user queue
WORKING = False
CANCEL = set()      # per-user cancel

bot = TelegramClient("bot", APP_ID, API_HASH).start(bot_token=BOT_TOKEN)
LOGS.info("🎬 Video Editor Bot Started")

# =========================
# 🌐 KEEP ALIVE (RENDER)
# =========================
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()

def run_server():
    port = int(os.environ.get("PORT", 8000))
    HTTPServer(("0.0.0.0", port), Handler).serve_forever()

threading.Thread(target=run_server, daemon=True).start()

# =========================
# ⚙ SETTINGS
# =========================
DEFAULT = {
    "resolution": 360,
    "crf": 30
}

# =========================
# 🔐 AUTH
# =========================
def auth(uid):
    return uid == DEV or uid in OWNER

# =========================
# 📊 PROGRESS BAR
# =========================
def bar(p):
    p = int(p)
    return "█" * (p // 10) + "░" * (10 - p // 10)

# =========================
# 🧠 SAFE EDIT (ANTI FLOOD)
# =========================
last_edit = {}

async def safe_edit(msg, text, uid):
    now = time.time()
    if uid in last_edit and now - last_edit[uid] < 3:
        return
    last_edit[uid] = now
    try:
        await msg.edit(text)
    except:
        pass

# =========================
# 🎛 START
# =========================
@bot.on(events.NewMessage(pattern="/start"))
async def start(e):
    if not auth(e.sender_id):
        return await e.reply("❌ Not allowed")

    USER_SETTINGS[e.sender_id] = DEFAULT.copy()

    await e.reply(
        "🎬 Video Editor Bot Ready",
        buttons=[
            [Button.inline("🎬 Compress", b"compress")],
            [Button.inline("❌ Cancel", b"cancel")]
        ]
    )

# =========================
# 🎛 CALLBACK
# =========================
@bot.on(events.CallbackQuery())
async def callback(e):
    uid = e.sender_id
    data = e.data.decode()

    if uid not in USER_SETTINGS:
        USER_SETTINGS[uid] = DEFAULT.copy()

    if data == "cancel":
        CANCEL.add(uid)
        QUEUE.pop(uid, None)
        await e.answer("Cancelled", alert=True)

    if data == "compress":
        await e.edit("📥 Send a video")

# =========================
# 📥 VIDEO HANDLER
# =========================
@bot.on(events.NewMessage(incoming=True))
async def video_handler(e):
    if not auth(e.sender_id):
        return

    if e.video or e.document:
        uid = e.sender_id

        # replace previous job
        QUEUE[uid] = {
            "media": e.media,
            "id": e.id
        }

        await e.reply("📥 Added to queue (latest only)")

# =========================
# 🧠 WORKER
# =========================
async def worker():
    global WORKING

    while True:
        try:
            if QUEUE and not WORKING:
                WORKING = True

                uid, job = list(QUEUE.items())[0]
                file = job["media"]

                settings = USER_SETTINGS.get(uid, DEFAULT)

                dl = f"downloads/{uid}.mp4"
                out = f"encode/{uid}.mp4"

                os.makedirs("downloads", exist_ok=True)
                os.makedirs("encode", exist_ok=True)

                msg = await bot.send_message(uid, "📥 Downloading...")

                # ================= DOWNLOAD =================
                start = time.time()

                def progress(cur, total):
                    if uid in CANCEL:
                        return

                    percent = cur * 100 / total if total else 0
                    speed = cur / (time.time() - start + 0.1)
                    eta = (total - cur) / (speed + 0.1)

                    asyncio.create_task(
                        safe_edit(
                            msg,
                            f"📥 Downloading...\n"
                            f"{bar(percent)} {percent:.1f}%\n"
                            f"⚡ {speed/1024:.1f} KB/s\n"
                            f"⏱ ETA {int(eta)}s",
                            uid
                        )
                    )

                await bot.download_media(file, file=dl, progress_callback=progress)

                if uid in CANCEL:
                    CANCEL.remove(uid)
                    WORKING = False
                    continue

                # ================= FFMPEG =================
                res = settings["resolution"]
                crf = settings["crf"]

                cmd = [
                    "ffmpeg", "-y",
                    "-i", dl,
                    "-vf", f"scale=-2:{res}",
                    "-c:v", "libx264",
                    "-preset", "veryfast",
                    "-tune", "fastdecode",
                    "-crf", str(crf),
                    "-pix_fmt", "yuv420p",
                    "-c:a", "aac",
                    "-b:a", "64k",
                    "-movflags", "+faststart",
                    out
                ]

                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.STDOUT
                )

                start_enc = time.time()

                while True:
                    line = await process.stdout.readline()
                    if not line:
                        break

                    line = line.decode(errors="ignore")

                    if "out_time_ms=" in line:
                        try:
                            t = int(line.split("=")[1]) / 1_000_000
                            speed = t / (time.time() - start_enc + 0.1)

                            await safe_edit(
                                msg,
                                f"🗜 Compressing...\n"
                                f"⏱ {t:.1f}s processed\n"
                                f"⚡ {speed:.2f}x speed",
                                uid
                            )
                        except:
                            pass

                if not os.path.exists(out):
                    await msg.edit("❌ Compression failed")
                    WORKING = False
                    continue

                # ================= UPLOAD =================
                up_start = time.time()

                def up_progress(cur, total):
                    if uid in CANCEL:
                        return

                    percent = cur * 100 / total if total else 0
                    speed = cur / (time.time() - up_start + 0.1)
                    eta = (total - cur) / (speed + 0.1)

                    asyncio.create_task(
                        safe_edit(
                            msg,
                            f"📤 Uploading...\n"
                            f"{bar(percent)} {percent:.1f}%\n"
                            f"⚡ {speed/1024:.1f} KB/s\n"
                            f"⏱ ETA {int(eta)}s",
                            uid
                        )
                    )

                org = Path(dl).stat().st_size
                com = Path(out).stat().st_size

                await bot.send_file(
                    uid,
                    out,
                    caption=f"🎬 Done\n📦 {org/1024/1024:.2f} → {com/1024/1024:.2f} MB",
                    progress_callback=up_progress
                )

                # ================= CLEAN =================
                QUEUE.pop(uid, None)
                WORKING = False

                os.remove(dl)
                os.remove(out)

            else:
                await asyncio.sleep(2)

        except Exception as e:
            LOGS.error(e)
            WORKING = False

# =========================
# 🚀 RUN
# =========================
with bot:
    bot.loop.run_until_complete(worker())
    bot.loop.run_forever()
