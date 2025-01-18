import discord, gspread, random
from discord.ext import commands
from oauth2client.service_account import ServiceAccountCredentials

# Bot features:
## Daily tips / facts


# Bot Setup
intents = discord.Intents.default()
intents.typing = False
intents.presences = False
bot = commands.Bot(command_prefix="!", intents=intents)

# Google Sheets Setup
def connect_command_sheet():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name("service_account.json", scope)
    client = gspread.authorize(creds)
    return client.open("Service Dog Commands").sheet1  # Adjust the sheet name.

cmd_sheet = connect_command_sheet()

def connect_tip_sheet():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name("service_account.json", scope)
    client = gspread.authorize(creds)
    return client.open("Service Dog Commands").sheet1  # Adjust the sheet name.

tip_sheet = connect_tip_sheet()

def connect_fact_sheet():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name("service_account.json", scope)
    client = gspread.authorize(creds)
    return client.open("Service Dog Commands").sheet1  # Adjust the sheet name.

fact_sheet = connect_fact_sheet()

# Fetch Training Commands from Google Sheets
@bot.command(name="command", help="Get a description of a training command. Usage: !command [keyword]")
async def fetch_command(ctx, *, keyword: str):
    try:
        data = cmd_sheet.get_all_records()
        for row in data:
            if keyword.lower() in row['Command'].lower():
                await ctx.send(f"**Command**: {row['Command']}\n**Description**: {row['Description']}")
                return
        await ctx.send("Sorry, I couldn't find that command.")
    except Exception as e:
        await ctx.send(f"An error occurred: {e}")

# Fun Dog Facts / Use Google Sheets for this?
DOG_FACTS = [
    "Dogs can learn more than 1000 words!",
    "A dog's nose print is unique, much like a human fingerprint.",
    "Service dogs can detect medical issues like seizures and low blood sugar.",
    "Dogs have three eyelids!",
    "Puppies are born deaf, but they develop hearing within a few weeks."
]

@bot.command(name="dogfacts", help="Get a fun dog fact!")
async def dog_facts(ctx):
    fact = random.choice(DOG_FACTS)
    await ctx.send(f"🐶 **Did you know?** {fact}")

# Fetch Training Commands from Google Sheets
@bot.command(name="facts", help="Get a fun dog fact!")
async def fetch_command(ctx, *, keyword: str):
    try:
        data = fact_sheet.get_all_records()
        fact = random.choice(data)
        await ctx.send(f"🐶 **Did you know?** {fact}")            
    except Exception as e:
        await ctx.send(f"An error occurred: {e}")

# Command: tip / Also move to use sheets
TIPS = [
    "Consistency is key when training your dog!",
    "Always end training sessions on a positive note.",
    "Short, frequent training sessions are better than long, infrequent ones.",
    "Reward your dog with treats, praise, or play to reinforce good behavior.",
    "Be patient and calm—training takes time and trust.",
]

@bot.command(name="tip", help="Get a motivational tip for dog training!")
async def tip(ctx):
    tip = random.choice(TIPS)
    await ctx.send(f"✨ **Tip of the Day**: {tip}")

# Bot Ready
@bot.event
async def on_ready():
    print(f"Bot is ready. Logged in as {bot.user}")

# Run Bot
bot.run("1326939453033418793")
