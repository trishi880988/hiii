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
        users_col.insert_one({"_id": user_id, "username": username})

    await message.reply("👋 Welcome! Send me a message and I'll forward it to the admin.")

# जब कोई user message भेजे, admin को forward करो (हर user का अलग thread रहेगा)
@app.on_message(filters.private & ~filters.command("start"))
async def handle_messages(client, message: Message):
    user_id = message.from_user.id
    username = message.from_user.username or "Unknown"

    if user_id == ADMIN_ID:
        return  # Admin से message नहीं लेना

    # Store message in MongoDB
    users_col.update_one(
        {"_id": user_id},
        {"$push": {"chat": {"from_user": message.text}}},
        upsert=True
    )

    # User का message admin को forward करो, user ID के साथ
    forwarded_message = await client.send_message(
        ADMIN_ID,
        f"📩 **New Message from** [{username}](tg://user?id={user_id}) (`{user_id}`)\n📝 **Message:** {message.text}",
        disable_web_page_preview=True
    )

    await message.reply("✅ Your message has been sent to the admin.")

# जब admin किसी user को reply करना चाहे, तो `/reply user_id message` भेजे
@app.on_message(filters.private & filters.command("reply") & filters.user(ADMIN_ID))
async def reply_to_user(client, message: Message):
    args = message.text.split(" ", 2)
    if len(args) < 3:
        return await message.reply("❌ Usage: /reply user_id message")

    try:
        user_id = int(args[1])  # Extract user ID
    except ValueError:
        return await message.reply("❌ Error: Invalid user ID.")

    reply_text = args[2]  # Extract message content

    # Admin का reply सही user को भेजो
    await client.send_message(user_id, f"👤 **Admin:** {reply_text}")

    # Store reply in database
    users_col.update_one(
        {"_id": user_id},
        {"$push": {"chat": {"from_admin": reply_text}}}
    )

    await message.reply(f"✅ Reply sent to user {user_id}!")

if __name__ == "__main__":
    print("🚀 Bot is running... Waiting for messages...")
    app.run()
