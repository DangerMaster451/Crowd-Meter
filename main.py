import discord
import os
from discord.ext import commands, tasks
from playwright.async_api import async_playwright
from google import genai
import random
import asyncio

class User():
    def __init__(self, member: discord.Member):
        self.member = member
        self.threshold:int = 3
        self.checkin_cooldown:int = 60
        self.message_cooldown:int = 0
        self.checkedIn:bool = False
        self.muted:bool = False

BASE_URL = "https://www.planetfitness.com/gyms"
DISCORD_TOKEN = os.environ["DISCORD_TOKEN"]
USERS:dict[str, User] = {}
PING_RATE = 15 * 60 #SECONDS
USE_AI = False

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='.', intents=intents)

google_client = genai.Client(api_key=os.environ["GOOGLE_TOKEN"])
prompts = ["In a short sentence, tell me the gym isn't busy and encourage me to go",
           "In a short sentence, tell me the gym isn't busy and aggressively tell me to go",
           "In a short sentence, tell me the gym isn't busy and tell me in a flirty way to go",
           "In a short sentence, tell me the gym isn't busy and warn me of the consequences of not going",
           "In a short sentence, tell me the gym isn't busy and aggressively convince me to go to the gym, or else",
           "In a short sentence, tell me the gym isn't busy and tell me a horrible way the world will end if I don't go to the gym",
           "Pretend to be a whiny girlfriend and in a short paragraph, tell me i'm getting too fat and you will leave me if I don't go to the gym",
           "In a brief sentence, pretend to be a gym trainer and aggressively tell me i'm fat and weak and that I need to hit the gym, and then remind me to shower after because I stink",
           "Pretend to be a sweet girlfriend, and encourage me to go to the gym so I can be big and strong",
           "Give me a one-sentence gym hype quote but make it unhinged.",
           "Write one sentence of passive-aggressive encouragement to go to the gym.",
           "In one sentence, guilt trip me for skipping the gym using the saddest possible imagery.",
           "Give me one sentence that makes skipping the gym sound like a war crime.",
           ]

async def scrape_crowd(slug: str, headless: bool) -> int:
    url = f"{BASE_URL}/{slug}"
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        page = await browser.new_page(user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ))
        await page.goto(url, wait_until="domcontentloaded")
        await page.wait_for_timeout(3000)
        all_meters = await page.locator("meter").all()
        indicator_bars = [
            m for m in all_meters
            if ("bg-accent-pink" in (await m.get_attribute("class") or "")
                or "bg-common-black" in (await m.get_attribute("class") or ""))
            and not (await m.get_attribute("id") or "").startswith("bar_")
        ]
        if indicator_bars:
            classes = [await m.get_attribute("class") or "" for m in indicator_bars]
            pink_count = sum(1 for c in classes if "bg-accent-pink" in c)
        else:
            pink_count = -1
        await browser.close()
        return pink_count
    
async def genEncouragement() -> str:
    prompt = prompts[random.randint(0, len(prompts)-1)]
    print(prompt)

    try:
        response = google_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        return response.text #type: ignore
    except Exception as e:
        print(f"AI error: {e}")
        return "the gym isn't busy, you should go!"

async def sendGymReminder(user:User):
    channel = await user.member.create_dm()
    if USE_AI:
        await channel.send(f"{user.member.mention}, {await genEncouragement()}") #type: ignore
    else:
        await channel.send(f"{user.member.mention}, the gym isn't busy, you should go!") #type: ignore

    user.muted = True
    async def clear_after():
        await asyncio.sleep(user.message_cooldown)
        user.muted = False

    asyncio.create_task(clear_after())

async def mailAllReminders(gymValue, recipients: list[User]):
    window_seconds = PING_RATE
    useable_seconds = window_seconds * 0.8
    delay = useable_seconds / len(recipients) if len(recipients) > 1 else 0

    async def run():
        for recipient in recipients:
            await sendGymReminder(recipient)
            await asyncio.sleep(delay)

    asyncio.create_task(run())

@bot.command()
async def ping(ctx):
    await ctx.send('pong')

@bot.command()
async def gymLevel(ctx):
    await ctx.send(await scrape_crowd("hanford-ca", headless=True))

@bot.command()
async def threshold(ctx, *args) -> None:
    if ctx.author.name not in USERS:
        await ctx.send("You must subscribe to set your threshold (.subscribe)")
        return
    if args == ():
        await ctx.send(f"{ctx.author.mention}, You're threshold is set to {USERS[ctx.author.name].threshold}")
        return 

    try:
        int(args[0])
    except ValueError as e:
        await ctx.send("Threshold must be a number")
        return

    if int(args[0]) > 0 and int(args[0]) <= 10:
        USERS[ctx.author.name].threshold = int(args[0])
        await ctx.send(f"Updated threshold to {USERS[ctx.author.name].threshold}")
        return
    else:
        await ctx.send("Threshold must be between 1 and 10")
        return
    
@bot.command()
async def cooldown(ctx, *args) -> None:
    if ctx.author.name not in USERS:
        await ctx.send("You must subscribe to set your cooldown (.subscribe)")
        return
    if args == ():
        await ctx.send(f"{ctx.author.mention}, You're cooldown is set to {USERS[ctx.author.name].message_cooldown} hours")
        return 

    try:
        int(args[0])
    except ValueError as e:
        await ctx.send("Cooldown must be a number")
        return

    if int(args[0]) >= 0 and int(args[0]) <= 72:
        USERS[ctx.author.name].message_cooldown = int(args[0])
        await ctx.send(f"Updated cooldown to {USERS[ctx.author.name].message_cooldown} hours")
        return
    else:
        await ctx.send("Cooldown must be between 0 and 72 hours")
        return

@bot.command()
async def subscribe(ctx):
    user = User(ctx.author)
    USERS[user.member.name] = user
    channel = await user.member.create_dm()
    await channel.send("Thanks for subscribing!")

@bot.command()
async def unsubscribe(ctx):
    user = User(ctx.author)
    del USERS[user.member.name]
    channel = await user.member.create_dm()
    await channel.send("Sorry to see you go")

@bot.command()
async def checkIn(ctx):
    if ctx.author.name not in USERS:
        await ctx.send("You must subscribe before checking in (.subscribe)")
        return
    user = User(ctx.author)
    USERS[user.member.name] = user
    user.checkedIn = True
    await ctx.send(f"{user.member.mention}, Congrats on making it!")

    async def clear_after():
        await asyncio.sleep(user.checkin_cooldown)
        user.checkedIn = False

    asyncio.create_task(clear_after())

@bot.command()
async def resetCheckIn(ctx):
    if ctx.author.name not in USERS:
        await ctx.send("You must subscribe before resetting (.subscribe)")
        return
    user = User(ctx.author)
    USERS[user.member.name] = user
    user.checkedIn = False
    await ctx.send(f"{user.member.mention}, Reset successfully")

@tasks.loop(seconds=PING_RATE)
async def scrape():
    value = await scrape_crowd('hanford-ca', True)
    recipients = []
    log = bot.get_channel(1514762219387224164)
    await log.send(value) #type: ignore

    for user in USERS.values():
        if value <= user.threshold and user.checkedIn == False and user.muted == False:
            recipients.append(user)

    await mailAllReminders(value, recipients)
    
@bot.event
async def on_ready():
    print("Ready")
    scrape.start()

bot.run(DISCORD_TOKEN)