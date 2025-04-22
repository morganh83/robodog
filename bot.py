import aiohttp, random, json, pytz, discord, os
from discord.ext import commands, tasks
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

used_tips = set()
used_challenges = set()

DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

TIPS_FILE = os.path.join(DATA_DIR, "used_tips.json")
CHALLENGES_FILE = os.path.join(DATA_DIR, "used_challenges.json")

BOT_TOKEN = os.getenv("BOT_TOKEN")
TIP_URL = os.getenv("TIP_URL")
CHALLENGE_URL = os.getenv("CHALLENGE_URL")

GENERAL_CHANNEL_ID = int(os.getenv("GENERAL_CHANNEL_ID"))
CHALLENGE_CHANNEL_ID = int(os.getenv("CHALLENGE_CHANNEL_ID"))

# Install URL: https://discord.com/oauth2/authorize?client_id=1326939453033418793&scope=bot&permissions=689342466112

def load_used(path):
    try:
        with open(path, "r") as f:
            return set(json.load(f))
    except (FileNotFoundError, json.JSONDecodeError):
        return set()

def save_used(path, used_set):
    with open(path, "w") as f:
        json.dump(list(used_set), f)

used_tips = load_used(TIPS_FILE)
used_challenges = load_used(CHALLENGES_FILE)

async def fetch_data(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            return await resp.json()

def rotate_item(data, used_set):
    unused = [item for item in data if json.dumps(item, sort_keys=True) not in used_set]
    if not unused:
        used_set.clear()
        unused = data.copy()
    choice = random.choice(unused)
    used_set.add(json.dumps(choice, sort_keys=True))
    
    return choice

async def post_daily_tip():
    channel = bot.get_channel(GENERAL_CHANNEL_ID)

    data = await fetch_data(TIP_URL)
    tip = rotate_item(data, used_tips)
    used_tips.add(json.dumps(tip, sort_keys=True))
    save_used(TIPS_FILE, used_tips)


    tip_type = tip.get("Type", "Tip")
    emoji_map = {
        "Dog": "🐶",
        "Training": "🎓",
        "Veteran": "🎖️",
        "Cue": "🐶",
        "Public Access": "🏙️",
        "Handler Wellness": "💪",
        "Team Bonding": "🤝",
        "Affirmation": "💖",
    }
    emoji = emoji_map.get(tip_type, "💡")

    embed = discord.Embed(
        title=f"**Daily Tip**",
        color=discord.Color.teal()
    )
    embed.add_field(
        name=f"{emoji} {tip_type} {emoji}",
        value=f"{tip['Tip']}",
        inline=False
    )
    embed.add_field(
        name="➖➖➖➖➖",
        value="**💬 Let’s Talk!**",
        inline=False
    )
    embed.add_field(
        name="",
        value=(
            "👍 Drop a reaction if this helped you!\n"
            "❓ Got questions or your own tip? Share it below.\n"
            "📣 Keep the convo going — you never know who it might help today."
        ),
        inline=False
    )

    await channel.send(embed=embed)

async def post_weekly_challenge():
    channel = bot.get_channel(GENERAL_CHANNEL_ID)

    data = await fetch_data(CHALLENGE_URL)
    challenge = rotate_item(data, used_challenges)
    used_challenges.add(json.dumps(challenge, sort_keys=True))
    save_used(CHALLENGES_FILE, used_challenges)


    embed = discord.Embed(
        title=f"🎯 **Weekly Challenge: {challenge['Action']}**",
        description=f"📘 *{challenge['Description']}*",
        color=discord.Color.gold()
    )
    embed.add_field(
        name="🔰 Recruit Level",
        value=challenge["Recruit"],
        inline=False
    )
    embed.add_field(
        name="🎖️ Operator Level",
        value=challenge["Operator"],
        inline=False
    )
    embed.add_field(
        name="🏅 Veteran Level",
        value=challenge["Veteran"],
        inline=False
    )
    embed.add_field(
        name="➖➖➖➖➖",
        value="**🛠️ HOW TO DO IT**",
        inline=False
    )
    embed.add_field(
        name="📍 Instructions:",
        value=challenge["How"],
        inline=False
    )
    embed.add_field(
        name="➖➖➖➖➖",
        value="**💬 Send It!**",
        inline=False
    )
    embed.add_field(
        name="",
        value=(
            "🐾 Post pics or videos, ask for feedback, share your wins!\n"
            "💡 Need help? Just ask! Our community is here for you.\n"
            f"📸 Head over to <#{CHALLENGE_CHANNEL_ID}> to post your progress!"
        ),
        inline=False
    )

    await channel.send(embed=embed)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    eastern = pytz.timezone("US/Eastern")

    scheduler = AsyncIOScheduler(timezone=eastern)
    scheduler.add_job(post_daily_tip, CronTrigger(hour=10, minute=0))  # 10 AM ET daily
    scheduler.add_job(post_weekly_challenge, CronTrigger(day_of_week="mon", hour=12, minute=0))  # 12 PM ET Mondays
    scheduler.start()

@bot.command(name="tip")
async def manual_tip(ctx):
    await post_daily_tip()

@bot.command(name="challenge")
async def manual_challenge(ctx):
    await post_weekly_challenge()

bot.run(BOT_TOKEN)