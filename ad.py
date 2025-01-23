import os
import psutil
import asyncio
from telethon import TelegramClient, events
from telethon.errors import SessionPasswordNeededError
from telethon.tl.functions.channels import LeaveChannelRequest

# Path to accounts file
ACCOUNTS_FILE = "accounts.txt"

# Folder for storing sessions
SESSIONS_FOLDER = "sessions"

# Ensure the sessions folder exists
if not os.path.exists(SESSIONS_FOLDER):
    os.mkdir(SESSIONS_FOLDER)

# In-memory storage for hosted accounts
hosted_accounts = {}

# Load accounts from the configuration file
def load_accounts():
    if not os.path.exists(ACCOUNTS_FILE):
        raise FileNotFoundError(f"Accounts file not found at {ACCOUNTS_FILE}. Please create it and add accounts in the format: API_ID|API_HASH|PHONE_NUMBER")

    accounts = []
    with open(ACCOUNTS_FILE, "r") as file:
        for line in file:
            line = line.strip()
            if line:
                try:
                    api_id, api_hash, phone_number = line.split("|")
                    accounts.append((int(api_id), api_hash, phone_number))
                except ValueError:
                    print(f"Invalid account format: {line}. Skipping...")
    return accounts

# Get server stats
def get_server_stats():
    cpu_usage = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    memory_usage = memory.percent
    return f"CPU Usage: {cpu_usage}%\nMemory Usage: {memory_usage}%"

# Command: /host
@bot.on(events.NewMessage(pattern="/host"))
async def host_accounts(event):
    accounts = load_accounts()

    for account in accounts:
        api_id, api_hash, phone_number = account
        session_name = f"{SESSIONS_FOLDER}/{phone_number.replace('+', '')}"  # Use phone number as session name

        if session_name in hosted_accounts:
            await event.reply(f"Account {phone_number} is already hosted.")
            continue

        client = TelegramClient(session_name, api_id, api_hash)
        try:
            await client.start(phone=phone_number)
            if not await client.is_user_authorized():
                await client.send_code_request(phone_number)
                await event.reply(f"Enter the code sent to {phone_number}:")

                @bot.on(events.NewMessage(from_user=event.sender_id))
                async def handle_code_response(code_event):
                    try:
                        await client.sign_in(phone_number, code_event.raw_text)
                        hosted_accounts[session_name] = client
                        await code_event.reply(f"Account {phone_number} hosted successfully!")
                    except Exception as e:
                        await code_event.reply(f"Failed to authenticate {phone_number}: {str(e)}")
                    finally:
                        bot.remove_event_handler(handle_code_response)
            else:
                hosted_accounts[session_name] = client
                await event.reply(f"Account {phone_number} hosted successfully!")
        except Exception as e:
            await event.reply(f"Failed to host account {phone_number}: {str(e)}")

# Command: /remove
@bot.on(events.NewMessage(pattern="/remove"))
async def remove_account(event):
    args = event.raw_text.split()
    if len(args) != 2:
        await event.reply("Usage: /remove <phone_number>")
        return

    phone_number = args[1]
    session_name = f"{SESSIONS_FOLDER}/{phone_number.replace('+', '')}"
    if session_name not in hosted_accounts:
        await event.reply(f"Account {phone_number} is not hosted.")
        return

    client = hosted_accounts.pop(session_name)
    await client.disconnect()
    os.remove(f"{session_name}.session")
    await event.reply(f"Account {phone_number} removed successfully.")

# Command: /accounts
@bot.on(events.NewMessage(pattern="/accounts"))
async def list_accounts(event):
    if not hosted_accounts:
        await event.reply("No accounts are currently hosted.")
    else:
        accounts = "\n".join([session.split("/")[-1] for session in hosted_accounts.keys()])
        await event.reply(f"Hosted accounts:\n{accounts}")

# Command: /stats
@bot.on(events.NewMessage(pattern="/stats"))
async def server_stats(event):
    stats = get_server_stats()
    await event.reply(f"Server Stats:\n{stats}")

# Initialize the bot
BOT_TOKEN = "YOUR_BOT_TOKEN"  # Replace with your bot token
bot = TelegramClient("bot", 0, "").start(bot_token=BOT_TOKEN)

print("Bot is running...")
bot.run_until_disconnected()
