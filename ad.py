import os
import json
import asyncio
from telethon import TelegramClient, events
from telethon.tl.functions.messages import GetHistoryRequest

# Configuration
CONFIG_PATH = "config.txt"
SESSIONS_FOLDER = "sessions"

# Ensure sessions folder exists
if not os.path.exists(SESSIONS_FOLDER):
    os.mkdir(SESSIONS_FOLDER)

# Load configuration from the file
def load_config():
    if not os.path.exists(CONFIG_PATH):
        raise FileNotFoundError(f"Configuration file {CONFIG_PATH} not found.")
    with open(CONFIG_PATH, "r") as f:
        return [line.strip().split("|") for line in f.readlines() if line.strip()]

# Initialize the bot
BOT_TOKEN = "8031831989:AAH8H2ZuKhMukDZ9cWG2Kgm18hEx835jb48"
API_ID = "26416419"
API_HASH = "c109c77f5823c847b1aeb7fbd4990cc4"
bot = TelegramClient("bot", API_ID, API_HASH).start(bot_token=BOT_TOKEN)

# In-memory storage for hosted accounts
hosted_accounts = {}

# Save account credentials
def save_account(session_name, api_id, api_hash, phone_number):
    data = {
        "api_id": api_id,
        "api_hash": api_hash,
        "phone_number": phone_number
    }
    with open(f"{SESSIONS_FOLDER}/{session_name}.json", "w") as f:
        json.dump(data, f)

# Load account credentials
def load_account(session_name):
    try:
        with open(f"{SESSIONS_FOLDER}/{session_name}.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return None

# Command: /host
@bot.on(events.NewMessage(pattern="/host"))
async def host_account(event):
    args = event.raw_text.split()
    if len(args) != 2:
        await event.reply("Usage: /host <session_name>")
        return

    session_name = args[1]
    config = load_config()

    if session_name in hosted_accounts:
        await event.reply(f"Session {session_name} is already hosted.")
        return

    for api_id, api_hash, phone_number in config:
        if session_name in phone_number:
            client = TelegramClient(f"{SESSIONS_FOLDER}/{session_name}", int(api_id), api_hash)
            try:
                await client.start(phone=phone_number)
                hosted_accounts[session_name] = client
                save_account(session_name, api_id, api_hash, phone_number)
                await event.reply(f"Account {session_name} hosted successfully!")
            except Exception as e:
                await event.reply(f"Failed to host account {session_name}: {str(e)}")
            return

    await event.reply(f"Configuration for session {session_name} not found in {CONFIG_PATH}.")

# Command: /forward
@bot.on(events.NewMessage(pattern="/forward"))
async def forward_messages(event):
    args = event.raw_text.split()
    if len(args) != 4:
        await event.reply("Usage: /forward <num_messages> <delay_seconds> <rounds>")
        return

    num_messages = int(args[1])
    delay_seconds = int(args[2])
    rounds = int(args[3])

    if not hosted_accounts:
        await event.reply("No accounts are currently hosted.")
        return

    for session_name, client in hosted_accounts.items():
        try:
            saved_messages = await client.get_input_entity("me")
            history = await client(GetHistoryRequest(
                peer=saved_messages,
                limit=num_messages,
                offset_id=0,
                offset_date=None,
                add_offset=0,
                max_id=0,
                min_id=0,
                hash=0
            ))

            if not history.messages:
                await event.reply(f"No messages found in Saved Messages for {session_name}.")
                continue

            messages_to_forward = history.messages[:num_messages]

            for round_num in range(rounds):
                for dialog in await client.get_dialogs():
                    if dialog.is_group:
                        group = dialog.entity
                        try:
                            for message in messages_to_forward:
                                await client.forward_messages(group, message)
                                print(f"Forwarded message to {group.title} using {session_name}.")
                                await asyncio.sleep(delay_seconds)
                        except Exception as e:
                            print(f"Failed to forward message to {group.title}: {e}")

                if round_num < rounds - 1:
                    print(f"Waiting {delay_seconds} seconds before starting the next round...")
                    await asyncio.sleep(delay_seconds)

        except Exception as e:
            await event.reply(f"Error while forwarding messages for {session_name}: {e}")

# Run the bot
print("Bot is running...")
bot.run_until_disconnected()
