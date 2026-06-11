import sys
import discord
import os
from discord.ext import commands
from playwright.async_api import async_playwright

BASE_URL = "https://www.planetfitness.com/gyms"
DISCORD_TOKEN = os.environ["DISCORD_TOKEN"]

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='.', intents=intents)


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
        
@bot.command()
async def on_ready(self):
    print('Logged on as', self.user)

@bot.command()
async def ping(ctx):
    await ctx.send('pong')

@bot.command()
async def gymLevel(ctx):
    await ctx.send(await scrape_crowd("hanford-ca", headless=True))

    

bot.run(DISCORD_TOKEN)

#print(scrape_crowd("hanford-ca", headless=True))