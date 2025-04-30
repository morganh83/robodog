import aiohttp, random, json, pytz, discord, os, time, logging, sys
from datetime import datetime
from discord.ext import commands, tasks
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from logging.handlers import TimedRotatingFileHandler

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)
CONFIG_FILE = "data/guild_config.json"
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

used_tips = set()
used_challenges = set()

TIP_TIME       = "10:00" # HH:MM 24-hour Eastern
CHALLENGE_TIME = "12:00" # HH:MM 24-hour Eastern

eastern = pytz.timezone("US/Eastern")
scheduler = AsyncIOScheduler(timezone=eastern)

def hm(s: str):
    h, m = map(int, s.split(":"))
    return h, m

DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

TIPS_FILE = os.path.join(DATA_DIR, "used_tips.json")
CHALLENGES_FILE = os.path.join(DATA_DIR, "used_challenges.json")

BOT_TOKEN = os.getenv("BOT_TOKEN")
# print(f"[INFO] BOT_TOKEN: {BOT_TOKEN}")
# print(f"[INFO] STORED TOKEN: {os.getenv("BOT_TOKEN")}")

TIP_URL = os.getenv("TIP_URL")
CHALLENGE_URL = os.getenv("CHALLENGE_URL")

handler = TimedRotatingFileHandler(
    filename=f"{LOG_DIR}/bot.log",
    when="D",           # rotate by day
    interval=30,        # …every 30 days
    backupCount=6,      # keep 6 old files
    encoding="utf-8"
)
fmt = "%(asctime)s  %(levelname)-7s  %(name)s  %(message)s"
handler.setFormatter(logging.Formatter(fmt))
logger = logging.getLogger("DeltaDog")     # root app logger
logger.setLevel(logging.INFO)
logger.addHandler(handler)
stream = logging.StreamHandler(sys.stdout)
stream.setFormatter(logging.Formatter(fmt))
logger.addHandler(stream)

def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {}
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)

def save_config(config):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)

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

@bot.event
async def on_command(ctx):
    logger.info("CMD  user=%s  guild=%s  cmd=%s  args=%s",
                ctx.author, ctx.guild and ctx.guild.name, ctx.command, ctx.args[2:])

@bot.event
async def on_command_completion(ctx):
    logger.info("OK   user=%s  cmd=%s", ctx.author, ctx.command)

@bot.event
async def on_command_error(ctx, error):
    logger.error("ERR  user=%s  cmd=%s  err=%s", ctx.author, ctx.command, error)
    await ctx.send(f"⚠️ Error: {error}")

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    print(f"Received message: {message.content} in guild {message.guild.name}")
    await bot.process_commands(message)


@bot.command(name="diagnose")
@commands.has_permissions(administrator=True)
async def diagnose(ctx):
    guild = ctx.guild
    await ctx.send(
        f"🔍 Guild ID: `{guild.id}`\n"
        f"Channels I can see: {len(guild.channels)}\n"
        f"My permissions here: {ctx.channel.permissions_for(guild.me)}"
    )

@bot.command(name="settipchannel")
@commands.has_permissions(administrator=True)
async def settipchannel(ctx):
    config = load_config()
    guild_id = str(ctx.guild.id)
    config.setdefault(guild_id, {})
    config[guild_id]["tip_channel"] = ctx.channel.id
    save_config(config)
    await ctx.send(f"✅ Tip channel set to: {ctx.channel.mention}")

@bot.command(name="setchallengechannel")
@commands.has_permissions(administrator=True)
async def setchallengechannel(ctx):
    config = load_config()
    guild_id = str(ctx.guild.id)
    config.setdefault(guild_id, {})
    config[guild_id]["challenge_channel"] = ctx.channel.id
    save_config(config)
    await ctx.send(f"✅ Challenge channel set to: {ctx.channel.mention}")

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

def get_configured_channel(guild_id, key):
    config = load_config()
    return config.get(str(guild_id), {}).get(key)

async def post_daily_tip(guild_id=None, channel=None):
    if not channel:
        if not guild_id:
            print("[ERROR] No guild ID or channel provided to post_daily_tip.")
            return
        channel_id = get_configured_channel(guild_id, "tip_channel")
        if not channel_id:
            print(f"[ERROR] No tip_channel configured for guild {guild_id}.")
            return
        channel = bot.get_channel(channel_id)
        if not channel:
            print(f"[ERROR] Channel ID {channel_id} not found in current bot context.")
            return

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

async def post_weekly_challenge(guild_id=None, channel=None):
    if not channel:
        if not guild_id:
            print("[ERROR] No guild ID or channel provided to post_weekly_challenge.")
            return
        channel_id = get_configured_channel(guild_id, "challenge_channel")
        if not channel_id:
            print(f"[ERROR] No challenge_channel configured for guild {guild_id}.")
            return
        channel = bot.get_channel(channel_id)
        if not channel:
            print(f"[ERROR] Channel ID {channel_id} not found in current bot context.")
            return

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
            f"📸 Head over to <#{channel_id}> to post your progress!"
        ),
        inline=False
    )

    await channel.send(embed=embed)


@scheduler.scheduled_job(CronTrigger(hour=hm(TIP_TIME)[0], minute=hm(TIP_TIME)[1], timezone=eastern))
async def scheduled_tips():
    for guild in bot.guilds:
        logger.info("[Tip job] sent tip to %s", guild.name)
        logger.warning("[Tip job] no TIP_URL response")
        await post_daily_tip(guild_id=guild.id)

@scheduler.scheduled_job(CronTrigger(day_of_week="mon", hour=hm(CHALLENGE_TIME)[0], minute=hm(CHALLENGE_TIME)[1], timezone=eastern))
async def scheduled_challenges():
    for guild in bot.guilds:
        logger.info("[Challenge job] sent tip to %s", guild.name)
        logger.warning("[Challenge job] no TIP_URL response")
        await post_weekly_challenge(guild_id=guild.id)

@bot.event
async def setup_hook():
    scheduler.start()
    print("[Scheduler] started")

@bot.event
async def on_ready():
    print(f"Bot is ready!")
    config = load_config()
    for guild in bot.guilds:
        guild_id = str(guild.id)
        config.setdefault(guild_id, {})
        config[guild_id]["name"] = guild.name
    save_config(config)

@bot.command(name="deltahelp")
@commands.has_permissions(administrator=True)
async def delta_help(ctx):
    embed = discord.Embed(
        title="📘 Delta Bot Commands",
        description="Here are the available admin commands for setting up Delta in this server:",
        color=discord.Color.blue()
    )

    embed.add_field(
        name="`!settipchannel`",
        value="Set the current channel to receive daily tips.",
        inline=False
    )
    embed.add_field(
        name="`!setchallengechannel`",
        value="Set the current channel to receive weekly challenges.",
        inline=False
    )
    embed.add_field(
        name="`!tip`",
        value="Manually trigger a daily tip post (uses configured channel).",
        inline=False
    )
    embed.add_field(
        name="`!challenge`",
        value="Manually trigger a weekly challenge post (uses configured channel).",
        inline=False
    )
    embed.add_field(
        name="`!deltahelp`",
        value="Display this command reference. (Admins only)",
        inline=False
    )
    embed.add_field(
        name="`!time`",
        value="Display the current Bot Time.",
        inline=False
    )
    await ctx.send(embed=embed)

@bot.event
async def on_guild_join(guild):
    config = load_config()
    guild_id = str(guild.id)
    
    if guild_id not in config:
        config[guild_id] = {
            "name": guild.name,
            "tip_channel": None,
            "challenge_channel": None
        }
        save_config(config)
        print(f"[INFO] Initialized config for new guild: {guild.name} ({guild_id})")

@bot.command(name="time")
async def bot_time_cmd(ctx):
    # naive datetime → whatever /etc/localtime is set to inside the container
    now   = datetime.now()
    tzstr = time.tzname[0]  # e.g., 'UTC', 'EST'
    await ctx.send(
        f"🕒 Bot clock: {now.strftime('%Y-%m-%d %H:%M:%S')} {tzstr}"
    )

@bot.command(name="tip")
async def manual_tip(ctx):
    await post_daily_tip(guild_id=ctx.guild.id)

@bot.command(name="challenge")
async def manual_challenge(ctx):
    await post_weekly_challenge(guild_id=ctx.guild.id)

bot.run(BOT_TOKEN)