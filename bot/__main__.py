from . import *
from .config import *
from .worker import *
from .devtools import *
from .FastTelethon import *

import os
import asyncio
import time
import itertools
from datetime import datetime as dt
from pathlib import Path

# 🔥 Render PORT FIX
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running")

def run_server():
    port = int(os.environ.get("PORT", 8000))
    server = HTTPServer(("0.0.0.0", port), Handler)
    server.serve_forever()

threading.Thread(target=run_server, daemon=True).start()

LOGS.info("🚀 Starting Bot...")

try:
    bot.start(bot_token=BOT_TOKEN)
except Exception as er:
    LOGS.error(er)

# ✅ AUTH CHECK FIX
def is_authorized(user_id):
    return user_id in OWNER or user_id == DEV


######## COMMANDS ########

@bot.on(events.NewMessage(pattern="/start"))
async def _(e):
    if not is_authorized(e.sender_id):
        return await e.reply("❌ Not Authorized")
    await start(e)

@bot.on(events.NewMessage(pattern="/setcode"))
async def _(e):
    if not is_authorized(e.sender_id):
        return await e.reply("❌ Not Authorized")
    await coding(e)

@bot.on(events.NewMessage(pattern="/getcode"))
async def _(e):
    if not is_authorized(e.sender_id):
        return await e.reply("❌ Not Authorized")
    await getcode(e)

@bot.on(events.NewMessage(pattern="/showthumb"))
async def _(e):
    if not is_authorized(e.sender_id):
        return await e.reply("❌ Not Authorized")
    await getthumb(e)

@bot.on(events.NewMessage(pattern="/logs"))
async def _(e):
    if not is_authorized(e.sender_id):
        return await e.reply("❌ Not Authorized")
    await getlogs(e)

@bot.on(events.NewMessage(pattern="/cmds"))
async def _(e):
    if not is_authorized(e.sender_id):
        return await e.reply("❌ Not Authorized")
    await zylern(e)

@bot.on(events.NewMessage(pattern="/ping"))
async def _(e):
    if not is_authorized(e.sender_id):
        return await e.reply("❌ Not Authorized")
    await up(e)

@bot.on(events.NewMessage(pattern="/sysinfo"))
async def _(e):
    if not is_authorized(e.sender_id):
        return await e.reply("❌ Not Authorized")
    await sysinfo(e)

@bot.on(events.NewMessage(pattern="/leech"))
async def _(e):
    if not is_authorized(e.sender_id):
        return await e.reply("❌ Not Authorized")
    await dl_link(e)

@bot.on(events.NewMessage(pattern="/help"))
async def _(e):
    if not is_authorized(e.sender_id):
        return await e.reply("❌ Not Authorized")
    await ihelp(e)

@bot.on(events.NewMessage(pattern="/renew"))
async def _(e):
    if not is_authorized(e.sender_id):
        return await e.reply("❌ Not Authorized")
    await renew(e)

@bot.on(events.NewMessage(pattern="/clear"))
async def _(e):
    if not is_authorized(e.sender_id):
        return await e.reply("❌ Not Authorized")
    await clearqueue(e)

@bot.on(events.NewMessage(pattern="/speed"))
async def _(e):
    if not is_authorized(e.sender_id):
        return await e.reply("❌ Not Authorized")
    await test(e)


######## AUTO THUMB ########

@bot.on(events.NewMessage(incoming=True))
async def _(event):
    if not is_authorized(event.sender_id):
        return

    if event.photo:
        thumb_path = "thumb.jpg"
        if os.path.exists(thumb_path):
            os.remove(thumb_path)

        await event.client.download_media(event.media, file=thumb_path)
        await event.reply("✅ Thumbnail Saved")


######## AUTO ENCODE ########

@bot.on(events.NewMessage(incoming=True))
async def _(e):
    if not is_authorized(e.sender_id):
        return
    await encod(e)


######## MAIN WORKER ########

async def something():
    for i in itertools.count():

        try:
            if i % 50 == 0:
                LOGS.info("💡 Bot alive...")

            if not WORKING and QUEUE:

                user = OWNER[0]
                e = await bot.send_message(user, "📥 Downloading...")

                s = dt.now()

                try:
                    dl, file = QUEUE[list(QUEUE.keys())[0]]
                    dl = "downloads/" + dl

                    with open(dl, "wb") as f:
                        await download_file(client=bot, location=file, out=f)

                except Exception as r:
                    LOGS.error(r)
                    WORKING.clear()
                    QUEUE.pop(list(QUEUE.keys())[0])
                    continue

                es = dt.now()

                out = f"encode/{Path(dl).stem}.mkv"

                thum = "thumb.jpg" if os.path.exists("thumb.jpg") else None

                await e.edit("🗜 Compressing...")

                cmd = f'ffmpeg -i "{dl}" {ffmpegcode[0]} "{out}" -y'

                process = await asyncio.create_subprocess_shell(
                    cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
                )

                stdout, stderr = await process.communicate()

                # ✅ FIXED ERROR CHECK
                if process.returncode != 0:
                    err = stderr.decode()
                    await e.edit(f"❌ FFmpeg Error:\n{err}")
                    QUEUE.pop(list(QUEUE.keys())[0])
                    continue

                await e.edit("📤 Uploading...")

                if not os.path.exists(out) or os.path.getsize(out) == 0:
                    await e.edit("❌ Output file invalid")
                    QUEUE.pop(list(QUEUE.keys())[0])
                    continue

                await e.client.send_file(
                    e.chat_id,
                    file=out,
                    force_document=True,
                    thumb=thum,
                    caption="✅ Done"
                )

                QUEUE.pop(list(QUEUE.keys())[0])

                if os.path.exists(dl):
                    os.remove(dl)
                if os.path.exists(out):
                    os.remove(out)

            else:
                await asyncio.sleep(3)

        except Exception as err:
            LOGS.error(err)


######## START ########

LOGS.info("✅ Bot started successfully")

with bot:
    bot.loop.run_until_complete(something())
    bot.loop.run_forever()
