import os
import asyncio
from datetime import datetime, timezone

import discord
from discord.ext import commands

from analyzer import clean
from database import setup_database, save, stats
from scanner import scan_opportunities

TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("DISCORD_CHANNEL_ID", "0"))
RUN_ONCE = os.getenv("RUN_ONCE", "false").lower() == "true"

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

def make_embed(item):
    e = discord.Embed(title="🚀 " + item["title"], description=clean(item["problem"], 700), url=item.get("url"), timestamp=datetime.now(timezone.utc))
    e.add_field(name="💰 Opportunity", value=f"{item['score']}/10", inline=True)
    e.add_field(name="🎯 Customer", value=item["customer"], inline=True)
    e.add_field(name="💡 Product angle", value=item["idea"], inline=False)
    e.add_field(name="📍 Source", value=item["source"], inline=True)
    e.set_footer(text="Opportunity Scout V5")
    return e

async def scan_and_send(channel):
    print("🔎 Scanning Reddit + Hacker News + GitHub Issues...")
    results = await scan_opportunities()
    print(f"Found {len(results)} candidates.")
    for item in results:
        await save(item)
        await channel.send(embed=make_embed(item))
        await asyncio.sleep(0.5)
    if not results:
        await channel.send("🔎 Scan completed. No new high-signal opportunities this time.")

@bot.event
async def on_ready():
    await setup_database()
    print(f"🟢 Online as {bot.user}")
    if RUN_ONCE:
        channel = bot.get_channel(CHANNEL_ID)
        if channel:
            await scan_and_send(channel)
        else:
            print("❌ Channel not found. Check DISCORD_CHANNEL_ID.")
        await bot.close()

@bot.command()
async def ping(ctx):
    await ctx.send("🟢 Opportunity Scout V5 online")

@bot.command()
async def hunt(ctx):
    await ctx.send("🔎 Manual scan started...")
    await scan_and_send(ctx.channel)

@bot.command(name="stats")
async def stats_command(ctx):
    total, best = await stats()
    await ctx.send(f"📊 Found: **{total}** opportunities | Best score: **{best}/10**")

if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN is missing")

bot.run(TOKEN)
