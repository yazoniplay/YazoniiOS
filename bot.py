import os
import re
import asyncio
from datetime import datetime, timezone

import aiohttp
import discord
from discord.ext import commands, tasks

TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("DISCORD_CHANNEL_ID", "0"))

SUBREDDITS = [
    "SaaS",
    "Entrepreneur",
    "smallbusiness",
    "SideProject",
    "startups",
    "webdev",
    "programming",
    "Minecraft",
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
    "frustrated",
    "hate",
    "struggle",
    "takes too long",
    "automate",
    "alternative",
    "better than",
    "missing feature",
    "wish",
    "need help",
    "any solution",
    "recommend",
    "recommendation",
    "problem with",
]

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)

seen_posts = set()


def score_post(title, body, upvotes, comments):
    text = f"{title} {body}".lower()

    score = 0

    for keyword in KEYWORDS:
        if keyword in text:
            score += 1

    if len(body) > 300:
        score += 2

    if len(body) > 800:
        score += 1

    money_words = [
        "pay",
        "paid",
        "money",
        "cost",
        "price",
        "customer",
        "revenue",
        "business",
        "company",
    ]

    for word in money_words:
        if word in text:
            score += 1

    if upvotes > 10:
        score += 1

    if comments > 10:
        score += 1

    return min(score, 10)


def clean_text(text, limit=700):
    text = re.sub(r"\s+", " ", text).strip()

    if len(text) > limit:
        return text[:limit] + "..."

    return text


async def fetch_reddit(session, subreddit):
    url = f"https://www.reddit.com/r/{subreddit}/new.json?limit=50"

    headers = {
        "User-Agent": "OpportunityScout/1.1"
    }

    try:
        async with session.get(
            url,
            headers=headers,
            timeout=15
        ) as response:

            if response.status != 200:
                return []

            data = await response.json()

            results = []

            for child in data["data"]["children"]:
                post = child["data"]

                post_id = post.get("id")

                if not post_id or post_id in seen_posts:
                    continue

                title = post.get("title", "")
                body = post.get("selftext", "")

                score = score_post(
                    title,
                    body,
                    post.get("ups", 0),
                    post.get("num_comments", 0)
                )

                if score >= 2:
                    results.append({
                        "id": post_id,
                        "title": title,
                        "body": body,
                        "score": score,
                        "url": "https://reddit.com" + post.get("permalink", ""),
                        "source": f"r/{subreddit}"
                    })

            return results

    except Exception as e:
        print("Error:", e)
        return []


async def search_opportunities():

    opportunities = []

    async with aiohttp.ClientSession() as session:

        for subreddit in SUBREDDITS:
            posts = await fetch_reddit(
                session,
                subreddit
            )

            opportunities.extend(posts)

            await asyncio.sleep(1)

    opportunities.sort(
        key=lambda x: x["score"],
        reverse=True
    )

    for item in opportunities:
        seen_posts.add(item["id"])

    return opportunities[:10]


def create_embed(item):

    score = item["score"]

    if score >= 8:
        rating = "🔥 High Potential"
    elif score >= 5:
        rating = "🟠 Interesting"
    else:
        rating = "🟡 Worth Checking"

    embed = discord.Embed(
        title="💡 " + item["title"],
        url=item["url"],
        description=clean_text(item["body"]),
        timestamp=datetime.now(timezone.utc)
    )

    embed.add_field(
        name="Score",
        value=f"{score}/10 {rating}"
    )

    embed.add_field(
        name="Source",
        value=item["source"]
    )

    embed.set_footer(
        text="Opportunity Scout"
    )

    return embed


async def send_results(channel):

    opportunities = await search_opportunities()

    if not opportunities:
        await channel.send(
            "🔎 No strong opportunities found yet."
        )
        return

    await channel.send(
        f"🚀 Found {len(opportunities)} possible opportunities!"
    )

    for item in opportunities:
        await channel.send(
            embed=create_embed(item)
        )

        await asyncio.sleep(1)


@bot.event
async def on_ready():

    print(
        f"Logged in as {bot.user}"
    )

    if not daily_scan.is_running():
        daily_scan.start()


@tasks.loop(hours=6)
async def daily_scan():

    channel = bot.get_channel(CHANNEL_ID)

    if channel:
        await send_results(channel)


@bot.command()
async def hunt(ctx):

    await ctx.send(
        "🔎 Hunting..."
    )

    results = await search_opportunities()

    for item in results[:5]:
        await ctx.send(
            embed=create_embed(item)
        )


@bot.command()
async def ping(ctx):

    await ctx.send(
        "🟢 Online"
    )


bot.run(TOKEN)
