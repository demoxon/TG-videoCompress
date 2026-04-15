from . import *
from .config import *
from .FastTelethon import *

import os, asyncio, time, itertools
from datetime import datetime as dt
from pathlib import Path

# 🔥 RENDER PORT FIX
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot running")

def run_server():
    import os
    port = int(os.environ.get("PORT", 8000))
    server = HTTPServer(("0.0.0.0", port), Handler)
    server.serve_forever()

threading.Thread(target=run_server, daemon=True).start()

# START BOT
bot.start(bot_token=BOT_TOKEN)
LOGS.info("🚀 Bot Started")

# AUTH
def auth(uid):
    return uid in OWNER or uid == DEV

# COMMAND
@bot.on(events.NewMessage(pattern="/start"))
async def _(e):
    if not auth(e.sender_id):
        return await e.reply("❌ Not allowed")
    await e.reply("✅ Bot is running")

# AUTO ENCODE
@bot.on(events.NewMessage(incoming=True))
async def _(e):
    if not auth(e.sender_id):
        return
    await encod(e)

# MAIN LOOP
async def worker():
    while True:
        try:
            if QUEUE:

                user = OWNER[0]
                e = await bot.send_message(user, "📥 Downloading...")

                file_id, file = list(QUEUE.items())[0]

                # 🚀 FAST DOWNLOAD
                tt = time.time()
                dl = await fast_download(
                    e,
                    file_id,
                    file,
                    progress_callback=lambda d, t: asyncio.create_task(
                        progress(d, t, e, tt, "📥 Downloading...")
                    )
                )

                dl = "downloads/" + dl

                # FILE SIZE
                size = Path(dl).stat().st_size / (1024 * 1024)

                # 🎯 SMART COMPRESSION
                if size > 300:
                    code = "-c:v libx264 -preset ultrafast -crf 30 -vf scale=854:-2 -c:a aac -b:a 96k -threads 0"
                else:
                    code = ffmpegcode[0]

                out = f"encode/{Path(dl).stem}.mkv"

                await e.edit("🗜 Compressing...")

                cmd = f'ffmpeg -i "{dl}" {code} "{out}" -y'

                process = await asyncio.create_subprocess_shell(
                    cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )

                while True:
                    await asyncio.sleep(5)
                    if process.returncode is not None:
                        break
                    await e.edit("🗜 Compressing... ⏳")

                stdout, stderr = await process.communicate()

                if process.returncode != 0:
                    await e.edit(f"❌ Error:\n{stderr.decode()}")
                    QUEUE.pop(file_id)
                    continue

                # SIZE STATS
                org = Path(dl).stat().st_size
                com = Path(out).stat().st_size
                per = 100 - ((com / org) * 100)

                await e.edit(
                    f"📊 Done\n\n"
                    f"Original: {round(org/1024/1024,2)} MB\n"
                    f"Compressed: {round(com/1024/1024,2)} MB\n"
                    f"Saved: {round(per,2)}%"
                )

                # 🚀 FAST UPLOAD
                ttt = time.time()
                await bot.send_message(user, "📤 Uploading...")

                with open(out, "rb") as f:
                    await upload_file(
                        client=bot,
                        file=f,
                        name=out,
                        progress_callback=lambda d, t: asyncio.create_task(
                            progress(d, t, e, ttt, "📤 Uploading...")
                        ),
                    )

                # CLEAN
                QUEUE.pop(file_id)
                os.remove(dl)
                os.remove(out)

            else:
                await asyncio.sleep(3)

        except Exception as err:
            LOGS.error(err)

# RUN
with bot:
    bot.loop.run_until_complete(worker())
    bot.loop.run_forever()
