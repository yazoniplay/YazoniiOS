import os
import re
import asyncio
from datetime import datetime, timezone

import aiohttp
import aiosqlite
import discord

from discord.ext import commands, tasks


TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("DISCORD_CHANNEL_ID"))


DATABASE = "opportunities.db"


intents = discord.Intents.default()
intents.message_content = True


bot = commands.Bot(
    command_prefix="!",
    intents=intents
)


PROBLEM_WORDS = [
    "i hate",
    "annoying",
    "frustrating",
    "problem",
    "issue",
    "broken",
    "manual",
    "takes too long",
    "wish there was",
    "need a tool",
    "looking for",
    "alternative",
    "hard to",
    "struggle"
]


MONEY_WORDS = [
    "pay",
    "paid",
    "business",
    "customer",
    "company",
    "subscription",
    "expensive"
]


async def setup_db():

    async with aiosqlite.connect(DATABASE) as db:

        await db.execute("""
        CREATE TABLE IF NOT EXISTS opportunities(
            id TEXT PRIMARY KEY,
            title TEXT,
            score INTEGER,
            source TEXT,
            date TEXT
        )
        """)

        await db.commit()



def clean(text):

    return re.sub(
        r"\s+",
        " ",
        text
    ).strip()



def score_problem(title, body):

    text = (
        title + " " + body
    ).lower()


    score = 0


    for word in PROBLEM_WORDS:

        if word in text:
            score += 2


    for word in MONEY_WORDS:

        if word in text:
            score += 2


    if len(body) > 500:
        score += 1


    return min(score,10)



async def already_seen(post_id):

    async with aiosqlite.connect(DATABASE) as db:

        cur = await db.execute(
            "SELECT id FROM opportunities WHERE id=?",
            (post_id,)
        )

        result = await cur.fetchone()

        return result is not None



async def save(post):

    async with aiosqlite.connect(DATABASE) as db:

        await db.execute(
            """
            INSERT OR IGNORE INTO opportunities
            VALUES(?,?,?,?,?)
            """,
            (
                post["id"],
                post["title"],
                post["score"],
                post["source"],
                datetime.now(timezone.utc).isoformat()
            )
        )

        await db.commit()



async def reddit_scan():

    found=[]


    subs=[
        "Entrepreneur",
        "smallbusiness",
        "SaaS",
        "SideProject",
        "startups"
    ]


    headers={
        "User-Agent":"OpportunityScoutV4"
    }


    async with aiohttp.ClientSession() as session:

        for sub in subs:

            url=f"https://www.reddit.com/r/{sub}/new.json?limit=20"


            try:

                async with session.get(
                    url,
                    headers=headers
                ) as r:


                    data=await r.json()


                    for item in data["data"]["children"]:

                        post=item["data"]


                        pid=post["id"]


                        if await already_seen(pid):
                            continue


                        title=post.get("title","")
                        body=post.get("selftext","")


                        score=score_problem(
                            title,
                            body
                        )


                        if score >= 6:

                            found.append({

                                "id":pid,

                                "title":title,

                                "body":body,

                                "score":score,

                                "source":
                                "Reddit"

                            })


            except Exception as e:

                print(
                    "Reddit error",
                    e
                )


    return found



def embed(post):

    e=discord.Embed(

        title="🚀 Opportunity Found",

        description=
        clean(post["title"]),

        timestamp=datetime.now(
            timezone.utc
        )

    )


    e.add_field(
        name="Score",
        value=f"{post['score']}/10"
    )


    e.add_field(
        name="Source",
        value=post["source"]
    )


    e.set_footer(
        text="Opportunity Scout V4"
    )


    return e



async def scan():

    channel=bot.get_channel(
        CHANNEL_ID
    )


    if not channel:
        return


    opportunities=await reddit_scan()


    for item in opportunities:

        await save(item)


        await channel.send(
            embed=embed(item)
        )



@tasks.loop(minutes=10)
async def scanner():

    print(
        "Scanning..."
    )

    await scan()



@bot.event
async def on_ready():

    print(
        "Online",
        bot.user
    )

    await setup_db()


    if not scanner.is_running():

        scanner.start()



@bot.command()
async def ping(ctx):

    await ctx.send(
        "🟢 Scout online"
    )



@bot.command()
async def hunt(ctx):

    await ctx.send(
        "🔎 Manual scan started"
    )

    await scan()



bot.run(TOKEN)
