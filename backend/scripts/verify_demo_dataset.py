"""Verify all 5 demo roles can log in and access their seeded data without errors."""

import asyncio

from httpx import ASGITransport, AsyncClient

from app.main import app

DEMO_ACCOUNTS = [
    ("trainee@demo.vikas", "trainee", "/trainee/alerts", 200),
    ("institute@demo.vikas", "institute_admin", "/institute/flags", 200),
    ("panel@demo.vikas", "panel_member", "/panel/queue", 200),
    ("planner@demo.vikas", "planner", "/planner/map", 200),
    ("employer@demo.vikas", "employer", "/employer/my-validations", 200),
]


async def verify_demo_accounts() -> None:
    print("Verifying 5 demo user logins and primary screen data payloads...")
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        for email, expected_role, test_endpoint, expected_status in DEMO_ACCOUNTS:
            # 1. Login
            login_resp = await client.post(
                "/auth/login",
                json={"email": email, "password": "demo2026!"},
            )
            assert login_resp.status_code == 200, (
                f"Login failed for {email}: {login_resp.text}"
            )
            tokens = login_resp.json()
            access_token = tokens["access_token"]
            headers = {"Authorization": f"Bearer {access_token}"}

            # 2. Check /auth/me
            me_resp = await client.get("/auth/me", headers=headers)
            assert me_resp.status_code == 200, (
                f"/auth/me failed for {email}: {me_resp.text}"
            )
            me_data = me_resp.json()
            assert me_data["role"] == expected_role, (
                f"Role mismatch for {email}: got {me_data['role']}"
            )

            # 3. Check role-specific screen payload
            screen_resp = await client.get(test_endpoint, headers=headers)
            assert screen_resp.status_code == expected_status, (
                f"{test_endpoint} failed for {email} (status {screen_resp.status_code}): {screen_resp.text}"
            )
            print(
                f"  [PASS] {email} ({expected_role}): Logged in, payload from {test_endpoint} verified."
            )

    print("\nAll demo accounts and baseline screens verified successfully!")


if __name__ == "__main__":
    asyncio.run(verify_demo_accounts())
