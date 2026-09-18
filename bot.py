import os
import re
import asyncio
from datetime import datetime, timezone

import aiohttp
import discord
from discord.ext import commands, tasks


TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("DISCORD_CHANNEL_ID", "0"))


intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)


seen = set()


PROBLEM_WORDS = [
    "problem",
    "issue",
    "hate",
    "annoying",
    "frustrating",
    "struggle",
    "wish",
    "need",
    "looking for",
    "alternative",
    "missing",
    "broken",
    "slow",
    "expensive",
    "manual",
    "hard",
    "difficult",
    "takes too long",
    "automate",
    "tool",
    "software",
    "app"
]


MONEY_WORDS = [
    "pay",
    "paid",
    "customer",
    "business",
    "company",
    "revenue",
    "cost",
    "price",
    "subscription"
]


def analyze(title, text):

    content = (
        title + " " + text
    ).lower()

    score = 0

    for word in PROBLEM_WORDS:
        if word in content:
            score += 1

    for word in MONEY_WORDS:
        if word in content:
            score += 2

    if len(text) > 500:
        score += 2

    return min(score, 10)


def clean(text):

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text[:800]


async def reddit_search(session):

    subs = [
        "Entrepreneur",
        "SaaS",
        "smallbusiness",
        "SideProject",
        "startups",
        "webdev"
    ]

    results = []

    headers = {
        "User-Agent": "OpportunityScoutBot"
    }


    for sub in subs:

        try:

            url = (
                f"https://www.reddit.com/r/{sub}/hot.json?limit=20"
            )


            async with session.get(
                url,
                headers=headers
            ) as r:


                if r.status != 200:
                    continue


                data = await r.json()


                for item in data["data"]["children"]:

                    post = item["data"]

                    pid = post["id"]

                    if pid in seen:
                        continue


                    seen.add(pid)


                    score = analyze(
                        post.get("title",""),
                        post.get("selftext","")
                    )


                    if score >= 3:

                        results.append({

                            "title":
                                post.get("title",""),

                            "body":
                                post.get("selftext",""),

                            "score":
                                score,

                            "url":
                                "https://reddit.com"
                                +
                                post.get("permalink",""),

                            "source":
                                "Reddit r/" + sub
                        })


        except Exception as e:
            print(
                "Reddit error:",
                e
            )


    return results



async def hackernews_search(session):

    results = []

    try:

        url = (
            "https://hn.algolia.com/api/v1/search?"
            "query=problem%20software"
        )


        async with session.get(url) as r:

            data = await r.json()


            for hit in data["hits"][:20]:

                title = hit.get(
                    "title",
                    ""
                )


                score = analyze(
                    title,
                    ""
                )


                if score >= 2:

                    results.append({

                        "title":
                            title,

                        "body":
                            "Hacker News discussion",

                        "score":
                            score,

                        "url":
                            hit.get(
                                "url",
                                ""
                            ),

                        "source":
                            "Hacker News"

                    })


    except Exception as e:

        print(
            "HN error:",
            e
        )


    return results



async def find_opportunities():

    async with aiohttp.ClientSession() as session:

        results = []

        results += await reddit_search(session)

        results += await hackernews_search(session)


    results.sort(
        key=lambda x:x["score"],
        reverse=True
    )


    return results[:10]



def create_embed(item):

    score = item["score"]


    if score >= 8:

        level = "🔥 Huge potential"

    elif score >= 5:

        level = "🟠 Interesting"

    else:

        level = "🟡 Worth checking"



    embed = discord.Embed(

        title="💡 " + item["title"],

        description=clean(
            item["body"]
        ),

        url=item["url"],

        timestamp=datetime.now(
            timezone.utc
        )

    )


    embed.add_field(

        name="Opportunity Score",

        value=f"{score}/10 {level}"

    )


    embed.add_field(

        name="Source",

        value=item["source"]

    )


    embed.set_footer(

        text="Opportunity Scout V2"

    )


    return embed



async def send_scan(channel):

    opportunities = await find_opportunities()


    if not opportunities:

        await channel.send(
            "🔎 No opportunities found this scan."
        )

        return



    await channel.send(

        f"🚀 Found {len(opportunities)} possible ideas"

    )


    for item in opportunities:

        await channel.send(

            embed=create_embed(item)

        )

        await asyncio.sleep(1)




@bot.event
async def on_ready():

    print(
        "Online:",
        bot.user
    )


    if not scanner.is_running():

        scanner.start()



@tasks.loop(hours=6)
async def scanner():

    channel = bot.get_channel(
        CHANNEL_ID
    )


    if channel:

        await send_scan(
            channel
        )



@bot.command()
async def ping(ctx):

    await ctx.send(
        "🟢 Opportunity Scout online"
    )



@bot.command()
async def hunt(ctx):

    await ctx.send(
        "🔎 Searching..."
    )

    await send_scan(
        ctx.channel
    )



bot.run(TOKEN)
