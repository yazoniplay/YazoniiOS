import os
import asyncio
import platform
import time
import traceback
from datetime import datetime, timezone

import discord
from discord.ext import commands

from analyzer import clean
from database import setup_database, save, stats
from scanner import scan_opportunities
from ai import ask_gemini

TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("DISCORD_CHANNEL_ID", "0"))
RUN_ONCE = os.getenv("RUN_ONCE", "false").lower() == "true"

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

STARTED_AT = datetime.now(timezone.utc)
LAST_SCAN = None
LAST_SCAN_COUNT = 0
LAST_ERROR = None
SCAN_LOCK = asyncio.Lock()

def uptime_text():
    seconds = int((datetime.now(timezone.utc) - STARTED_AT).total_seconds())
    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    parts = []
    if days: parts.append(f"{days}d")
    if hours: parts.append(f"{hours}h")
    if minutes: parts.append(f"{minutes}m")
    parts.append(f"{seconds}s")
    return " ".join(parts)

def make_embed(item):
    e = discord.Embed(title="🚀 " + item["title"], description=clean(item["problem"], 700), url=item.get("url"), timestamp=datetime.now(timezone.utc))
    e.add_field(name="💰 Opportunity", value=f"{item['score']}/10", inline=True)
    e.add_field(name="🎯 Customer", value=item["customer"], inline=True)
    e.add_field(name="💡 Product angle", value=item["idea"], inline=False)
    e.add_field(name="📍 Source", value=item["source"], inline=True)
    e.set_footer(text="Yazoni Right Hand Man • Opportunity Radar")
    return e

async def scan_and_send(channel):
    global LAST_SCAN, LAST_SCAN_COUNT, LAST_ERROR
    if SCAN_LOCK.locked():
        await channel.send("⚠️ A scan is already running.")
        return
    async with SCAN_LOCK:
        try:
            results = await scan_opportunities()
            LAST_SCAN = datetime.now(timezone.utc)
            LAST_SCAN_COUNT = len(results)
            LAST_ERROR = None
            for item in results:
                await save(item)
                await channel.send(embed=make_embed(item))
                await asyncio.sleep(0.5)
            if not results:
                await channel.send("🔎 Scan complete — no new high-signal opportunities.")
        except Exception as exc:
            LAST_ERROR = f"{type(exc).__name__}: {exc}"
            print(traceback.format_exc())
            await channel.send("🔴 Scan failed. Use !status or !logs for diagnostics.")

def status_embed():
    e = discord.Embed(title="🧠 YAZONI OPS", description="Right Hand Man operational dashboard", timestamp=datetime.now(timezone.utc))
    e.add_field(name="Bot", value="🟢 ONLINE", inline=True)
    e.add_field(name="Discord", value=f"🟢 {round(bot.latency * 1000)}ms", inline=True)
    e.add_field(name="Scout", value="🟢 READY" if not SCAN_LOCK.locked() else "🟡 SCANNING", inline=True)
    e.add_field(name="Last scan", value=LAST_SCAN.strftime("%Y-%m-%d %H:%M UTC") if LAST_SCAN else "Never", inline=True)
    e.add_field(name="Results", value=str(LAST_SCAN_COUNT), inline=True)
    e.add_field(name="Uptime", value=uptime_text(), inline=True)
    e.add_field(name="Database", value="🟢 OK", inline=True)
    e.add_field(name="Errors", value="🔴 " + LAST_ERROR if LAST_ERROR else "🟢 0", inline=False)
    e.set_footer(text=f"Python {platform.python_version()} • YRH V2")
    return e

@bot.event
async def on_ready():
    await setup_database()
    print(f"🟢 YAZONI RIGHT HAND MAN online as {bot.user}")
    if RUN_ONCE:
        channel = bot.get_channel(CHANNEL_ID)
        if channel:
            await scan_and_send(channel)
        else:
            print("❌ Channel not found. Check DISCORD_CHANNEL_ID.")
        await bot.close()

@bot.command()
async def ping(ctx):
    started = time.perf_counter()
    msg = await ctx.send("🏓 Measuring...")
    ms = round((time.perf_counter() - started) * 1000)
    await msg.edit(content=f"🏓 Pong — Discord API response: {ms}ms | Gateway: {round(bot.latency * 1000)}ms")

@bot.command()
async def status(ctx):
    await ctx.send(embed=status_embed())

@bot.command()
async def hunt(ctx):
    await ctx.send("🔎 Opportunity hunt started.")
    await scan_and_send(ctx.channel)

@bot.command(name="stats")
async def stats_command(ctx):
    total, best = await stats()
    await ctx.send(f"📊 Opportunities found: {total} | Best score: {best}/10")

@bot.command(name="ask")
async def ask(ctx, *, prompt: str = ""):
    if not prompt.strip():
        await ctx.send("🧠 Usage: !ask <message>")
        return
    async with ctx.typing():
        reply = await ask_gemini(prompt.strip())
    if len(reply) <= 1900:
        await ctx.send(reply)
    else:
        for i in range(0, len(reply), 1900):
            await ctx.send(reply[i:i + 1900])
            await asyncio.sleep(0.2)

@bot.command()
async def logs(ctx):
    if LAST_ERROR:
        await ctx.send(f"🔴 Latest error\n{clean(LAST_ERROR, 1500)}")
    else:
        await ctx.send("🟢 No runtime errors recorded since this process started.")

@bot.command()
async def system(ctx):
    await ctx.send(
        f"🖥️ SYSTEM\nOS: {platform.system()} {platform.release()}\n"
        f"Python: {platform.python_version()}\nUptime: {uptime_text()}\n"
        f"Bot latency: {round(bot.latency * 1000)}ms"
    )

@bot.command()
async def helpme(ctx):
    await ctx.send(
        "🧠 YAZONI RIGHT HAND MAN\n\n"
        "!status — operational dashboard\n"
        "!ping — latency check\n"
        "!hunt — run opportunity scan\n"
        "!stats — opportunity statistics\n"
        "!logs — latest runtime error\n"
        "!system — safe system telemetry\n"
        "!ask <message> — talk to Gemini\n"
        "!helpme — command list"
    )

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    await bot.process_commands(message)

    if bot.user and bot.user.mentioned_in(message) and not message.mention_everyone:
        prompt = message.content
        prompt = prompt.replace(f"<@{bot.user.id}>", "").replace(f"<@!{bot.user.id}>", "").strip()
        if prompt:
            async with message.channel.typing():
                reply = await ask_gemini(prompt)
            if len(reply) <= 1900:
                await message.reply(reply, mention_author=False)
            else:
                for i in range(0, len(reply), 1900):
                    await message.channel.send(reply[i:i + 1900])
                    await asyncio.sleep(0.2)

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    print("Command error:", repr(error))
    await ctx.send(f"⚠️ Command error: {clean(str(error), 500)}")

if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN is missing")

bot.run(TOKEN)
