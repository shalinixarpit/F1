import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message
from config import API_ID, API_HASH, BOT_TOKEN

# ——————————————————————————————————————————————
bot = Client("bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

active_jobs = {}
print("🔄 Active jobs cleared on startup.")

# ——————————————————————————————————————————————
def extract_public_link(link: str):
    """Only extract public channel links like t.me/ChannelName/123"""
    import re
    match = re.match(r"https://t\.me/([^/]+)/(\d+)", link)
    if match:
        return match.group(1), int(match.group(2))
    return None, None

async def fetch_message(chat_id, msg_id):
    try:
        return await bot.get_messages(chat_id, msg_id)
    except Exception as e:
        print(f"[Fetch Error] chat={chat_id} msg_id={msg_id}: {e}")
        return None

async def forward_message(msg, dest_chat):
    try:
        await msg.copy(chat_id=dest_chat)
        return True
    except Exception as e:
        print(f"[Forward Error] {e}")
        return False

# ——————————————————————————————————————————————
@bot.on_message(filters.command("start", prefixes="/"))
async def start_forwarding(c: Client, m: Message):
    user_id = m.from_user.id
    if user_id in active_jobs:
        return await m.reply("❗ Already running a batch. Use /cancel to stop it.")

    active_jobs[user_id] = True

    parts = m.text.split(maxsplit=1)
    if len(parts) != 2:
        active_jobs.pop(user_id, None)
        return await m.reply("❗ Send command like:\n`/start https://t.me/SomeChannel/123`", quote=True)

    link = parts[1]
    chat_id, start_id = extract_public_link(link)
    if not chat_id:
        active_jobs.pop(user_id, None)
        return await m.reply("❗ Only public channel links are supported.", quote=True)

    dest_chat = "-1002927666549"  # 🔹 Your destination chat ID
    total_count = 1000              # 🔹 Number of messages to forward
    batch_size = 20                # 🔹 Send 20 messages at a time
    rest_time = 30                 # 🔹 Wait 30 seconds between batches
    sent_count = 0

    progress_msg = await m.reply("🚀 Starting forwarding…", quote=True)

    for offset in range(total_count):
        if not active_jobs.get(user_id):
            await progress_msg.edit("🚫 Cancelled by user.")
            return

        msg_id = start_id + offset
        msg = await fetch_message(chat_id, msg_id)
        if msg:
            success = await forward_message(msg, dest_chat)
            if success:
                sent_count += 1
            status = f"{offset+1}/{total_count}: {'✅ Done' if success else '⚠️ Error'}"
        else:
            status = f"{offset+1}/{total_count}: ❌ Not found"

        await progress_msg.edit(status)
        await asyncio.sleep(0.5)

        # 💤 Pause every 20 messages (except the last batch)
        if (offset + 1) % batch_size == 0 and (offset + 1) < total_count:
            await progress_msg.edit(
                f"⏸️ Resting for {rest_time} seconds… ({offset+1}/{total_count} done)"
            )
            await asyncio.sleep(rest_time)

    active_jobs.pop(user_id, None)
    await m.reply(f"✅ Done! ({sent_count}/{total_count} succeeded)", quote=True)

# ——————————————————————————————————————————————
@bot.on_message(filters.command("cancel", prefixes="/"))
async def cancel_forwarding(c: Client, m: Message):
    user_id = m.from_user.id
    if user_id in active_jobs:
        active_jobs.pop(user_id, None)
        await m.reply("🛑 Cancelled the process.")
    else:
        await m.reply("❗ No active job found.")

# ——————————————————————————————————————————————
if __name__ == "__main__":
    bot.run()
