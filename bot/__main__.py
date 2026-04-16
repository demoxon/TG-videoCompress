from .config import *

import os, asyncio, time, signal, threading
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from telethon import events, Button, TelegramClient

# =========================
# 🌐 PORT BIND (RENDER FIX)
# =========================
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot Running")

    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()

def run_server():
    port = int(os.environ.get("PORT", 10000))  # 🔥 IMPORTANT
    server = HTTPServer(("0.0.0.0", port), Handler)
    print(f"🌐 Server running on port {port}")
    server.serve_forever()

threading.Thread(target=run_server, daemon=True).start()

# =========================
# 🔥 GLOBAL STATE
# =========================
USER_SETTINGS = {}
QUEUE = {}
WORKING = False
CANCEL = False
PROCESS = None
LAST_EDIT = {}

bot = TelegramClient("bot", APP_ID, API_HASH).start(bot_token=BOT_TOKEN)

def auth(uid):
    return uid in OWNER or uid == DEV

# =========================
# ⚙ DEFAULT SETTINGS
# =========================
DEFAULT = {
    "resolution": 360,
    "crf": 30
}

# =========================
# 🧠 SAFE EDIT (ANTI FLOOD)
# =========================
async def safe_edit(msg, text, delay=2):
    now = time.time()
    key = msg.id

    if key in LAST_EDIT and now - LAST_EDIT[key] < delay:
        return

    try:
        await msg.edit(text[:4000])
        LAST_EDIT[key] = now
    except:
        pass

# =========================
# 🎛 UI
# =========================
def main_menu():
    return [
        [Button.inline("🎬 Compress", b"compress")],
        [Button.inline("⚙ Settings", b"settings")],
        [Button.inline("❌ Cancel", b"cancel")]
    ]

def settings_menu():
    return [
        [Button.inline("📐 Resolution", b"res")],
        [Button.inline("🎛 Quality", b"preset")],
        [Button.inline("🔙 Back", b"back")]
    ]

def preset_menu():
    return [
        [Button.inline("⚡ Fast", b"p_fast")],
        [Button.inline("⚖ Balanced", b"p_bal")],
        [Button.inline("🎥 High", b"p_high")],
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
# 🚀 COMMANDS
# =========================
@bot.on(events.NewMessage(pattern="/start"))
async def start(e):
    if not auth(e.sender_id):
        return
    USER_SETTINGS[e.sender_id] = DEFAULT.copy()
    await e.reply("🎬 PRO Video Editor Bot", buttons=main_menu())

@bot.on(events.NewMessage(pattern="/help"))
async def help_cmd(e):
    await e.reply(
        "📘 Help Menu\n\n"
        "🎬 Send video to compress\n"
        "⚙ Change settings\n"
        "❌ Cancel anytime\n\n"
        "/start /help /cancel"
    )

@bot.on(events.NewMessage(pattern="/cancel"))
async def cancel_cmd(e):
    global CANCEL, PROCESS
    CANCEL = True
    if PROCESS:
        PROCESS.kill()
    await e.reply("❌ Task Cancelled")

# =========================
# 🎛 CALLBACK
# =========================
@bot.on(events.CallbackQuery())
async def callback(e):
    global CANCEL, PROCESS

    uid = e.sender_id
    data = e.data.decode()

    USER_SETTINGS.setdefault(uid, DEFAULT.copy())

    if data == "settings":
        return await e.edit("⚙ Settings", buttons=settings_menu())

    if data == "back":
        return await e.edit("🎬 Menu", buttons=main_menu())

    if data == "preset":
        return await e.edit("🎛 Quality", buttons=preset_menu())

    if data == "res":
        return await e.edit("📐 Resolution", buttons=res_menu())

    if data == "p_fast":
        USER_SETTINGS[uid]["crf"] = 35
        await e.answer("Fast")

    if data == "p_bal":
        USER_SETTINGS[uid]["crf"] = 30
        await e.answer("Balanced")

    if data == "p_high":
        USER_SETTINGS[uid]["crf"] = 26
        await e.answer("High")

    if data == "r240":
        USER_SETTINGS[uid]["resolution"] = 240
        await e.answer("240p")

    if data == "r360":
        USER_SETTINGS[uid]["resolution"] = 360
        await e.answer("360p")

    if data == "r720":
        USER_SETTINGS[uid]["resolution"] = 720
        await e.answer("720p")

    if data == "cancel":
        CANCEL = True
        if PROCESS:
            PROCESS.kill()
        await e.answer("Cancelled ❌", alert=True)

# =========================
# 📥 VIDEO HANDLER
# =========================
@bot.on(events.NewMessage(incoming=True))
async def video_handler(e):
    global QUEUE, CANCEL

    if not auth(e.sender_id):
        return

    if WORKING:
        return await e.reply("⏳ Already processing...")

    if e.video or e.document:
        QUEUE[e.id] = e.media
        CANCEL = False
        await e.reply("📥 Added to queue")

# =========================
# 🧠 WORKER
# =========================
async def worker():
    global WORKING, CANCEL, PROCESS

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

                msg = await bot.send_message(user, "🚀 Starting...")

                # ================= DOWNLOAD =================
                dl = f"downloads/{file_id}.mp4"
                start = time.time()

                def dl_progress(cur, total):
                    if CANCEL:
                        return
                    mb_cur = cur / (1024*1024)
                    mb_tot = total / (1024*1024)
                    speed = cur / (time.time() - start + 0.1)

                    asyncio.create_task(
                        safe_edit(msg,
                            f"📥 Downloading\n\n"
                            f"📦 {mb_cur:.2f}/{mb_tot:.2f} MB\n"
                            f"⚡ {speed/1024:.1f} KB/s"
                        )
                    )

                await bot.download_media(file, file=dl, progress_callback=dl_progress)

                if CANCEL:
                    WORKING = False
                    continue

                # ================= COMPRESS =================
                res = settings["resolution"]
                crf = settings["crf"]
                out = f"encode/{file_id}.mkv"

                await safe_edit(msg, "🗜 Compressing...")

                cmd = [
                    "ffmpeg", "-y",
                    "-i", dl,
                    "-vf", f"scale=-2:{res}",
                    "-c:v", "libx264",
                    "-preset", "ultrafast",
                    "-crf", str(crf),
                    "-progress", "pipe:1",
                    out
                ]

                PROCESS = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.STDOUT
                )

                while True:
                    if CANCEL:
                        PROCESS.kill()
                        break

                    line = await PROCESS.stdout.readline()
                    if not line:
                        break

                    if b"out_time_ms=" in line:
                        t = int(line.decode().split("=")[1]) / 1000000
                        await safe_edit(msg, f"🗜 Compressing\n⏱ {t:.1f}s processed")

                if CANCEL:
                    WORKING = False
                    continue

                # ================= UPLOAD =================
                org = Path(dl).stat().st_size
                com = Path(out).stat().st_size

                await bot.send_file(
                    user,
                    out,
                    caption=f"🎬 Done\n📦 {org/1024/1024:.2f} → {com/1024/1024:.2f} MB"
                )

                QUEUE.pop(file_id)
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
