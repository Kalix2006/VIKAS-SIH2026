import asyncio

import asyncpg


async def main():
    conn = await asyncpg.connect("postgresql://postgres@127.0.0.1:5433/vikas")
    await conn.execute("SET ROLE vikas_app")
    await conn.execute(
        "SELECT set_config('app.current_user_role', 'institute_admin', false)"
    )
    try:
        await conn.execute("""
            INSERT INTO alerts (id, target_role, target_id, skill_gap_id, message, generated_by, reviewed)
            SELECT gen_random_uuid(), 'planner'::alert_target_role, u.id, sg.id, 'test message', 'template'::alert_generator, false
            FROM users u, skill_gaps sg
            WHERE u.role = 'planner' LIMIT 1
        """)
        print("Insert successful!")
    except Exception as e:
        print("Error:", type(e), e)
    await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
