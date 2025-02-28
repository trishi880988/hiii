import os
import pymongo
from pyrogram import Client, filters
from pyrogram.types import Message
from dotenv import load_dotenv

load_dotenv()

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
MONGO_URL = os.getenv("MONGO_URL")

client = pymongo.MongoClient(MONGO_URL)
db = client["telegram_bot"]
users_col = db["users"]

app = Client("bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

@app.on_message(filters.command("start"))
async def start(client, message: Message):
    user_id = message.from_user.id
    user = users_col.find_one({"_id": user_id})
    if not user:
        users_col.insert_one({"_id": user_id, "username": message.from_user.username})
    await message.reply("👋 Welcome! Send me a message and I'll reply.")

@app.on_message(filters.private & ~filters.command("start"))
async def handle_messages(client, message: Message):
    user_id = message.from_user.id
    if user_id == ADMIN_ID:
        return  # Prevent bot from replying to admin
    await client.send_message(ADMIN_ID, f"📩 Message from {message.from_user.username}: {message.text}")
    await message.reply("✅ Your message has been sent to the admin.")

if __name__ == "__main__":
    print("🚀 Bot is running...")
    app.run()
