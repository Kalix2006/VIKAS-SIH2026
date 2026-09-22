
import asyncio, asyncpg, os
from dotenv import load_dotenv
load_dotenv()
url = os.getenv('DATABASE_URL').replace('postgresql+asyncpg://', 'postgresql://')
async def main():
    try:
        conn = await asyncpg.connect(url)
        print('Connected successfully!')
        
        exists = await conn.fetchval(
            "SELECT 1 FROM pg_roles WHERE rolname = 'vikas_app'"
        )
        if not exists:
            print('Creating role vikas_app...')
            await conn.execute("CREATE ROLE vikas_app NOLOGIN")
            await conn.execute("GRANT USAGE ON SCHEMA public TO vikas_app")
            await conn.execute("GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO vikas_app")
            await conn.execute("ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON TABLES TO vikas_app")
            await conn.execute("GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO vikas_app")
            await conn.execute("ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON SEQUENCES TO vikas_app")
            print('Role created and privileges granted.')
            
            await conn.execute("GRANT vikas_app TO postgres")
            print('Granted vikas_app to postgres user')
        else:
            print('Role vikas_app already exists.')
            
        await conn.close()
    except Exception as e:
        print(f'Error: {e.__class__.__name__}: {e}')
asyncio.run(main())

