import os as O
import re as R
import asyncio

from pyrogram import Client, filters
from pyrogram.types import Message

from config import API_ID, API_HASH, BOT_TOKEN, SESSION, LOG_CHANNEL, DEST_CHANNEL

# ——————————————————————————————————————————————
# Initialize Bot and User Clients
bot = Client(
    "bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

user = Client(
    "user",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION
)

# ——————————————————————————————————————————————
active_jobs = {}
print("🔄 All active jobs cleared on startup.")


# ——————————————————————————————————————————————
# Helper Functions
def extract_link(link: str):
    m1 = R.match(r"https://t\.me/c/(\d+)/(\d+)", link)
    m2 = R.match(r"https://t\.me/([^/]+)/(\d+)", link)
    if m1:
        return f"-100{m1.group(1)}", int(m1.group(2)), "private"
    if m2:
        return m2.group(1), int(m2.group(2)), "public"
    return None, None, None


async def fetch_message(bot_client, user_client, chat_id, msg_id, link_type):
    client = bot_client if link_type == "public" else user_client
    try:
        return await client.get_messages(chat_id, msg_id)
    except Exception as e:
        print(f"[Fetch Error] chat={chat_id} msg_id={msg_id}: {e}")
        return None


async def forward_or_send(bot_client, user_client, msg, dest_chat, link_type):
    try:
        if msg.media:
            if link_type == "private":
                path = await user_client.download_media(msg)
                await bot_client.send_document(dest_chat, path)
                await bot_client.send_document(LOG_CHANNEL, path)
                O.remove(path)
            else:
                await msg.copy(chat_id=dest_chat)
                await msg.copy(chat_id=LOG_CHANNEL)
            return "Done"

        elif msg.text:
            if link_type == "private":
                await bot_client.send_message(dest_chat, msg.text)
                await bot_client.send_message(LOG_CHANNEL, msg.text)
            else:
                await msg.copy(chat_id=dest_chat)
                await msg.copy(chat_id=LOG_CHANNEL)
            return "Done"

        else:
            return "Skipped"

    except Exception as e:
        return f"Error: {e}"


# ——————————————————————————————————————————————
# Commands
@bot.on_message(filters.command("start", prefixes="/"))
async def start_batch(c: Client, m: Message):
    user_id = m.from_user.id
    if user_id in active_jobs:
        return await m.reply("❗ A batch is already running. Use /cancel to stop it.")

    active_jobs[user_id] = True

    parts = m.text.split(maxsplit=1)
    if len(parts) != 2:
        active_jobs.pop(user_id, None)
        return await m.reply_text(
            "❗️ Usage:\n"
            "`/start https://t.me/SomePublicChannel/100`",
            quote=True
        )

    link = parts[1]
    chat_id, start_id, link_type = extract_link(link)
    if not chat_id:
        active_jobs.pop(user_id, None)
        return await m.reply_text("❗️ Invalid Telegram link.", quote=True)

    total_count = 1000
    batch_size = 20
    sent_success = 0

    progress_msg = await m.reply_text("Starting batch… 🐥", quote=True)

    for batch_offset in range(0, total_count, batch_size):
        for i in range(batch_size):
            if not active_jobs.get(user_id):
                await progress_msg.edit("🚫 Cancelled by user.")
                return

            current_index = batch_offset + i
            msg_id = start_id + current_index

            msg = await fetch_message(bot, user, chat_id, msg_id, link_type)
            if not msg:
                status = f"{current_index+1}/{total_count}: ❌ not found"
            else:
                result = await forward_or_send(bot, user, msg, DEST_CHANNEL, link_type)
                if result == "Done":
                    sent_success += 1
                status = f"{current_index+1}/{total_count}: {result}"

            try:
                await progress_msg.edit(status)
            except:  # Floodwait fix
                pass

            await asyncio.sleep(1)

        if batch_offset + batch_size < total_count:
            await progress_msg.edit(f"Sent {batch_offset + batch_size}/{total_count} — sleeping 30 s… 💤")
            await asyncio.sleep(30)

    active_jobs.pop(user_id, None)
    await m.reply_text(f"✅ All done! ({sent_success}/{total_count} succeeded)", quote=True)


@bot.on_message(filters.command("cancel", prefixes="/"))
async def cancel_batch(c: Client, m: Message):
    user_id = m.from_user.id
    if user_id in active_jobs:
        active_jobs.pop(user_id, None)
        await m.reply("🛑 Cancelling process... Done.")
    else:
        await m.reply("❗ No active job found.")


# ——————————————————————————————————————————————
# Run bot
if __name__ == "__main__":
    try:
        user.start()
        print("User session started.")
    except Exception as e:
        print("Failed to start user session:", e)

    bot.run()
