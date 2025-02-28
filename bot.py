import os
import pymongo
from pyrogram import Client, filters
from pyrogram.types import Message
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
MONGO_URL = os.getenv("MONGO_URL")

# Database setup
client = pymongo.MongoClient(MONGO_URL)
db = client["telegram_bot"]
users_col = db["users"]

# Initialize bot
app = Client("bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# जब user /start भेजे
@app.on_message(filters.command("start"))
async def start(client, message: Message):
    user_id = message.from_user.id
    username = message.from_user.username or "Unknown"

    # Check if user exists in database
    user = users_col.find_one({"_id": user_id})
    if not user:
        users_col.insert_one({"_id": user_id, "username": username, "chat": []})

    await message.reply("👋 Welcome! Send me a message and I'll forward it to the admin.")

# जब कोई user message भेजे, तो admin को forward करो (हर user के लिए अलग chat)
@app.on_message(filters.private & ~filters.command("start"))
async def handle_messages(client, message: Message):
    user_id = message.from_user.id
    username = message.from_user.username or "Unknown"
    text = message.text

    if user_id == ADMIN_ID:
        return  # Admin से message नहीं लेना

    # Store message in MongoDB
    users_col.update_one(
        {"_id": user_id},
        {"$push": {"chat": {"from_user": text}}},
        upsert=True
    )

    # Admin को user के नाम से अलग chat में message भेजो
    chat_tag = f"📩 **{username}** (`{user_id}`)\n📝 {text}"
    await client.send_message(ADMIN_ID, chat_tag)

    await message.reply("✅ Your message has been sent to the admin.")

# Admin जब किसी user को reply करना चाहे
@app.on_message(filters.private & filters.reply & filters.user(ADMIN_ID))
async def reply_to_user(client, message: Message):
    if not message.reply_to_message:
        return await message.reply("❌ Error: Reply to a user's message.")

    # Extract user_id from the forwarded message
    reply_text = message.text
    forwarded_message = message.reply_to_message.text
    user_id_str = forwarded_message.split("(`")[1].split("`)")[0]

    try:
        user_id = int(user_id_str)  # Convert user_id to integer
    except ValueError:
        return await message.reply("❌ Error: Invalid user ID.")

    # Admin का reply सही user को भेजो
    await client.send_message(user_id, f"👤 **Admin:** {reply_text}")

    # Store reply in MongoDB
    users_col.update_one(
        {"_id": user_id},
        {"$push": {"chat": {"from_admin": reply_text}}}
    )

    await message.reply(f"✅ Reply sent to {user_id}!")

if __name__ == "__main__":
    print("🚀 Bot is running... Waiting for messages...")
    app.run()
