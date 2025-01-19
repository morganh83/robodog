import discord, gspread, random, pytz
from discord.ext import commands, tasks
from oauth2client.service_account import ServiceAccountCredentials
from datetime import time

# Bot Setup
intents = discord.Intents.default()
intents.reactions = True  # Required for on_raw_reaction_add
intents.members = True     # Required to manage roles
bot = commands.Bot(command_prefix="!", intents=intents)

# Constants / Config
RULES_CHANNEL_ID = 123456789012345678
RULES_MESSAGE_ID = 987654321098765432
RULES_ROLE_NAME = "Member"

FACTS_CHANNEL_ID = 222222222222222222
TIPS_CHANNEL_ID = 333333333333333333

# Google Sheets Setup
def connect_sheet(sheet_name, worksheet=0):
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name("service_account.json", scope)
    client = gspread.authorize(creds)
    return client.open(sheet_name).get_worksheet(worksheet)

fact_sheet = connect_sheet("Service Dog Facts")
tip_sheet = connect_sheet("Service Dog Tips")

@bot.event
async def on_ready():
    print(f"Bot is ready. Logged in as {bot.user}")
    daily_facts.start()
    daily_tips.start()

@bot.event
async def on_raw_reaction_add(payload):
    # Grant role upon ✅ reaction on rules message
    if payload.message_id == RULES_MESSAGE_ID and str(payload.emoji) == "✅":
        guild = bot.get_guild(payload.guild_id)
        if guild is None:
            return
        role = discord.utils.get(guild.roles, name=RULES_ROLE_NAME)
        if not role:
            print(f"Role '{RULES_ROLE_NAME}' not found.")
            return
        member = guild.get_member(payload.user_id)
        if member and not member.bot:
            await member.add_roles(role)
            print(f"Assigned {RULES_ROLE_NAME} to {member.display_name}")

@tasks.loop(time=time(hour=9, minute=0, tzinfo=pytz.timezone('US/Eastern')))
async def daily_facts():
    channel = bot.get_channel(FACTS_CHANNEL_ID)
    if not channel:
        return
    data = fact_sheet.get_all_records()
    if not data:
        return
    row = random.choice(data)
    fact = row.get("Fact", "No fact found.")
    await channel.send(f"🐶 **Daily Dog Fact**: {fact}")

@tasks.loop(time=time(hour=10, minute=0, tzinfo=pytz.timezone('US/Eastern')))
async def daily_tips():
    channel = bot.get_channel(TIPS_CHANNEL_ID)
    if not channel:
        return
    data = tip_sheet.get_all_records()
    if not data:
        return
    row = random.choice(data)
    tip = row.get("Tip", "No tip found.")
    await channel.send(f"✨ **Daily Training Tip**: {tip}")

@bot.command(name="command", help="Get a description of a training command. Usage: !command [keyword]")
async def fetch_command(ctx, *, keyword: str):
    # Example of looking up a command from a sheet
    cmd_sheet = connect_sheet("Service Dog Commands")
    try:
        data = cmd_sheet.get_all_records()
        for row in data:
            if keyword.lower() in row['Command'].lower():
                await ctx.send(f"**Command**: {row['Command']}\n**Description**: {row['Description']}")
                return
        await ctx.send("Sorry, I couldn't find that command.")
    except Exception as e:
        await ctx.send(f"An error occurred: {e}")

@bot.command(name="setrules")
@commands.has_permissions(administrator=True)
async def set_rules(ctx, *, text: str):
    # Optional command to edit the pinned rules message
    channel = bot.get_channel(RULES_CHANNEL_ID)
    if not channel:
        await ctx.send("Rules channel not found!")
        return
    try:
        msg = await channel.fetch_message(RULES_MESSAGE_ID)
        await msg.edit(content=text)
        await ctx.send("Rules message updated successfully.")
    except discord.DiscordException as e:
        await ctx.send(f"Failed to edit rules message: {e}")

# Replace with your actual token
bot.run("YOUR_BOT_TOKEN")
