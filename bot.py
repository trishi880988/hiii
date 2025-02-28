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
messages_col = db["messages"]

# Initialize bot
app = Client(":memory:", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

@app.on_message(filters.command("start"))
async def start(client, message: Message):
    user_id = message.from_user.id
    username = message.from_user.username or "Unknown"

    # Check if user exists in database
    if not users_col.find_one({"_id": user_id}):
        users_col.insert_one({"_id": user_id, "username": username, "chat": []})

    await message.reply("👋 Welcome! Send me a message and I'll forward it to the admin.")

@app.on_message(filters.private & ~filters.command("start"))
async def handle_messages(client, message: Message):
    user_id = message.from_user.id
    username = message.from_user.username or "Unknown"

    if user_id == ADMIN_ID:
        return  # Prevent bot from replying to admin

    # Store message in MongoDB
    users_col.update_one(
        {"_id": user_id},
        {"$push": {"chat": {"from_user": message.text}}},
        upsert=True
    )

    # Send message to admin
    await client.send_message(
        ADMIN_ID,
        f"📩 **New Message from** [{username}](tg://user?id={user_id}) (`{user_id}`)\n📝 **Message:** {message.text}"
    )

    await message.reply("✅ Your message has been sent to the admin.")

@app.on_message(filters.reply & filters.text)
async def reply_to_user(client, message: Message):
    if message.reply_to_message:
        lines = message.reply_to_message.text.split("\n")
        user_info = [line for line in lines if "`" in line]  # Find the user ID line

        if user_info:
            user_id = int(user_info[0].split("`")[1])  # Extract user_id

            # Store reply in MongoDB
            users_col.update_one(
                {"_id": user_id},
                {"$push": {"chat": {"from_admin": message.text}}},
                upsert=True
            )

            # Send reply to user
            await client.send_message(user_id, f"👤 **Admin:** {message.text}")

if __name__ == "__main__":
    print("🚀 Bot is running... Waiting for messages...")
    app.run()
