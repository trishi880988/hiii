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

# जब कोई user /start भेजे
@app.on_message(filters.command("start"))
async def start(client, message: Message):
    user_id = message.from_user.id
    username = message.from_user.username or "Unknown"

    # Check if user exists in database
    user = users_col.find_one({"_id": user_id})
    if not user:
        users_col.insert_one({"_id": user_id, "username": username, "chat": []})

    await message.reply("👋 Welcome! Send me a message and I'll forward it to the admin.")

# जब कोई user message भेजे, admin को forward करो (हर user के लिए अलग chat)
@app.on_message(filters.private & ~filters.command("start"))
async def handle_messages(client, message: Message):
    user_id = message.from_user.id
    username = message.from_user.username or "Unknown"
    text = message.text

    if user_id == ADMIN_ID:
        return  # Admin के खुद के messages ignore करो

    # Store message in MongoDB
    users_col.update_one(
        {"_id": user_id},
        {"$push": {"chat": {"from_user": text}}},
        upsert=True
    )

    # Admin को user के नाम से अलग chat में message भेजो
    forwarded_msg = await client.send_message(
        ADMIN_ID, 
        f"📩 **{username}** (`{user_id}`)\n📝 {text}"
    )

    # MongoDB में store करो ताकि reply track हो सके
    users_col.update_one(
        {"_id": user_id},
        {"$set": {"last_message_id": forwarded_msg.message_id}}
    )

    await message.reply("✅ Your message has been sent to the admin.")

# ✅ Admin किसी भी user को सीधे reply कर सकता है
@app.on_message(filters.private & filters.reply & filters.user(ADMIN_ID))
async def reply_to_user(client, message: Message):
    replied_msg = message.reply_to_message
    if not replied_msg:
        return await message.reply("❌ Error: Reply to a user's message.")

    # Extract user_id from the original forwarded message
    for user in users_col.find():
        last_msg_id = user.get("last_message_id")
        if last_msg_id == replied_msg.message_id:
            user_id = user["_id"]
            break
    else:
        return await message.reply("❌ Error: User not found.")

    # Store reply in MongoDB
    users_col.update_one(
        {"_id": user_id},
        {"$push": {"chat": {"from_admin": message.text}}}
    )

    # Send reply to user
    await client.send_message(user_id, f"👤 **Admin:** {message.text}")

    await message.reply(f"✅ Reply sent to {user_id}!")

if __name__ == "__main__":
    print("🚀 Bot is running... Waiting for messages...")
    app.run()
