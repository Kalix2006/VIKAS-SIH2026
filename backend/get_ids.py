import asyncio, asyncpg, os
from dotenv import load_dotenv
load_dotenv()
url = os.getenv('DATABASE_URL').replace('postgresql+asyncpg://', 'postgresql://')
async def main():
    conn = await asyncpg.connect(url)
    trades = await conn.fetch('SELECT id, name FROM trades')
    print('--- TRADES ---')
    for t in trades:
        print(f"{t['name']}: {t['id']}")
    districts = await conn.fetch('SELECT id, name FROM districts')
    print('\n--- DISTRICTS ---')
    for d in districts:
        print(f"{d['name']}: {d['id']}")
    await conn.close()
asyncio.run(main())

