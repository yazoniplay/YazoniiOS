import aiosqlite
from datetime import datetime, timezone

DB = "opportunities.db"

async def setup_database():
    async with aiosqlite.connect(DB) as db:
        await db.execute("CREATE TABLE IF NOT EXISTS opportunities(id TEXT PRIMARY KEY,title TEXT,score INTEGER,source TEXT,url TEXT,found_at TEXT)")
        await db.commit()

async def seen(item_id):
    async with aiosqlite.connect(DB) as db:
        cur = await db.execute("SELECT 1 FROM opportunities WHERE id=?", (item_id,))
        return await cur.fetchone() is not None

async def save(item):
    async with aiosqlite.connect(DB) as db:
        await db.execute("INSERT OR IGNORE INTO opportunities VALUES(?,?,?,?,?,?)", (item["id"], item["title"], item["score"], item["source"], item.get("url",""), datetime.now(timezone.utc).isoformat()))
        await db.commit()

async def stats():
    async with aiosqlite.connect(DB) as db:
        total = (await (await db.execute("SELECT COUNT(*) FROM opportunities")).fetchone())[0]
        best = (await (await db.execute("SELECT COALESCE(MAX(score),0) FROM opportunities")).fetchone())[0]
        return total, best
