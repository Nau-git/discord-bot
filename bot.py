import os
import dotenv
dotenv.load_dotenv()
import logging

import discord
from discord.ext import commands
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger
from datetime import datetime, timedelta
from openai import OpenAI
from collections import defaultdict

token = os.getenv("TOKEN")
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')

oai_client = OpenAI(
    api_key=os.getenv("GEMINI_API_KEY"),
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
)

chat_history = defaultdict(list)


token = os.getenv("TOKEN")
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')

description = '''A reminder bot'''

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

# Initialize bot and scheduler
bot = commands.Bot(command_prefix='!', description=description, intents=intents)
scheduler = AsyncIOScheduler()


@bot.event
async def on_ready():
    # Start the scheduler when the bot is ready
    scheduler.start()
    print(f'{bot.user} is now online!')

@bot.event
async def on_message(message):

    await bot.process_commands(message)

    if message.author == bot.user:
        return

    username = str(message.author).split("#")[0]
    channel = str(message.channel.name)
    user_message = str(message.content)

    print(f'Message "{user_message}" by "{username}" on channel "{channel}"')

    if channel == "chat-with-gemini":
        # await bot.process_commands(message)
        
        channel_history = chat_history[message.channel.id]

        messages = [{"role": "system", "content": "You are a helpful assistant."}]
        messages.extend(channel_history)
        messages.append({"role": "user", "content": user_message})

        response = oai_client.chat.completions.create(
            model="gemini-1.5-flash",
            n=1,
            messages= messages
        )

        ai_msg = response.choices[0].message.content

        channel_history.append({"role": "user", "content": user_message})
        channel_history.append({"role": "assistant", "content": ai_msg})

        # Keep only last 10 messages to manage context length
        if len(channel_history) > 20:
            channel_history = channel_history[-20:]
        chat_history[message.channel.id] = channel_history

        await message.channel.send(ai_msg)

# Command to set reminders
@bot.command()
async def remindme(ctx, time: str, *, message: str):
    """Set a reminder. Example: !remindme 10m Take a break"""
    time_unit = time[-1]
    if time_unit not in 'smh':  # seconds, minutes, hours
        await ctx.send("Invalid time format. Use 's', 'm', or 'h' (e.g., 10m for 10 minutes).")
        return

    try:
        time_value = int(time[:-1])
        if time_unit == 's':
            remind_time = datetime.now() + timedelta(seconds=time_value)
        elif time_unit == 'm':
            remind_time = datetime.now() + timedelta(minutes=time_value)
        elif time_unit == 'h':
            remind_time = datetime.now() + timedelta(hours=time_value)

        # Schedule the reminder
        scheduler.add_job(
            send_reminder,
            trigger=DateTrigger(run_date=remind_time),
            args=[ctx.channel.id, message]
        )
        await ctx.send(f"Reminder set for {time_value} {time_unit}.")
    except ValueError:
        await ctx.send("Invalid time value. Please provide a number before the unit.")

async def send_reminder(channel_id, message):
    """Sends the reminder message to the specified channel."""
    channel = bot.get_channel(channel_id)
    if channel:
        await channel.send(f"⏰ Reminder: {message}")

bot.run(token, log_handler=handler, log_level=logging.DEBUG)








