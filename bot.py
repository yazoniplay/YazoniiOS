import os
import re
import asyncio
from datetime import datetime, timezone

import aiohttp
import discord
from discord.ext import commands, tasks

TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("DISCORD_CHANNEL_ID", "0"))

# Subreddits where people frequently discuss problems, products and ideas.
SUBREDDITS = [
    "SaaS",
    "Entrepreneur",
    "smallbusiness",
    "SideProject",
    "startups",
    "webdev",
    "programming",
]

KEYWORDS = [
    "is there a tool",
    "is there an app",
    "looking for a tool",
    "looking for software",
    "looking for an app",
    "does anyone know",
    "i wish there was",
    "would pay for",
    "need a tool",
    "need software",
    "need an app",
    "how do i automate",
    "manual",
    "tedious",
    "annoying",
    "painful",
    "problem",
]

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

seen_posts = set()


def score_post(title, body):
    text = f"{title} {body}".lower()
    score = 0

    for keyword in KEYWORDS:
        if keyword in text:
            score += 2

    # More detailed posts usually contain more useful information.
    if len(body) > 300:
        score += 2

    if len(body) > 800:
        score += 1

    # Money-related language is useful for opportunity discovery.
    money_words = [
        "pay",
        "paid",
        "money",
        "cost",
        "price",
        "customer",
        "revenue",
        "business",
    ]

    for word in money_words:
        if word in text:
            score += 1

    return min(score, 10)


def clean_text(text, limit=700):
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > limit:
        return text[:limit] + "..."
    return text


async def fetch_reddit(session, subreddit):
    url = f"https://www.reddit.com/r/{subreddit}/new.json?limit=25"

    headers = {
        "User-Agent": "OpportunityScout/1.0"
    }

    try:
        async with session.get(url, headers=headers, timeout=15) as response:
            if response.status != 200:
                return []

            data = await response.json()

            results = []

            for child in data.get("data", {}).get("children", []):
                post = child.get("data", {})

                post_id = post.get("id")
                title = post.get("title", "")
                body = post.get("selftext", "")
                permalink = post.get("permalink", "")

                if not post_id or post_id in seen_posts:
                    continue

                score = score_post(title, body)

                if score >= 4:
                    results.append({
                        "id": post_id,
                        "title": title,
                        "body": body,
                        "score": score,
                        "url": "https://reddit.com" + permalink,
                        "source": f"r/{subreddit}",
                    })

            return results

    except Exception as e:
        print(f"Reddit error: {e}")
        return []


async def search_opportunities():
    opportunities = []

    async with aiohttp.ClientSession() as session:
        for subreddit in SUBREDDITS:
            results = await fetch_reddit(session, subreddit)
            opportunities.extend(results)

            await asyncio.sleep(1)

    opportunities.sort(
        key=lambda x: x["score"],
        reverse=True
    )

    # Remove duplicates and remember posts.
    for opportunity in opportunities:
        seen_posts.add(opportunity["id"])

    return opportunities[:10]


def make_embed(opportunity):
    score = opportunity["score"]

    if score >= 8:
        rating = "🔥 HIGH"
    elif score >= 6:
        rating = "🟠 MEDIUM"
    else:
        rating = "🟡 LOW"

    embed = discord.Embed(
        title=f"💡 {opportunity['title']}",
        url=opportunity["url"],
        description=clean_text(opportunity["body"]),
        timestamp=datetime.now(timezone.utc),
    )

    embed.add_field(
        name="Opportunity Score",
        value=f"**{score}/10 — {rating}**",
        inline=True,
    )

    embed.add_field(
        name="Source",
        value=opportunity["source"],
        inline=True,
    )

    embed.set_footer(
        text="Opportunity Scout • Investigate before building"
    )

    return embed


async def send_opportunities(channel):
    opportunities = await search_opportunities()

    if not opportunities:
        await channel.send(
            "🔎 Searched the sources, but didn't find any strong new opportunities."
        )
        return

    await channel.send(
        f"🔎 **Opportunity Scout found {len(opportunities)} opportunities.**"
    )

    for opportunity in opportunities:
        await channel.send(
            embed=make_embed(opportunity)
        )

        await asyncio.sleep(1)


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

    if not daily_scan.is_running():
        daily_scan.start()


@tasks.loop(hours=6)
async def daily_scan():
    if CHANNEL_ID == 0:
        print("DISCORD_CHANNEL_ID is not configured.")
        return

    channel = bot.get_channel(CHANNEL_ID)

    if channel is None:
        print("Could not find Discord channel.")
        return

    await send_opportunities(channel)


@bot.command()
async def hunt(ctx, *, topic=""):
    """
    Manually search the opportunity database.
    Example: !hunt Minecraft
    """

    await ctx.send(
        f"🔎 Hunting for opportunities"
        + (f" related to **{topic}**..." if topic else "...")
    )

    opportunities = await search_opportunities()

    if topic:
        topic_lower = topic.lower()

        opportunities = [
            x for x in opportunities
            if topic_lower in (
                x["title"] + " " + x["body"]
            ).lower()
        ]

    if not opportunities:
        await ctx.send("No strong opportunities found.")
        return

    for opportunity in opportunities[:5]:
        await ctx.send(
            embed=make_embed(opportunity)
        )


@bot.command()
async def ping(ctx):
    await ctx.send("🟢 Opportunity Scout is online.")


if not TOKEN:
    raise RuntimeError(
        "DISCORD_TOKEN environment variable is missing."
    )


bot.run(TOKEN)
