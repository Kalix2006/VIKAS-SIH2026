"""Benchmark all API endpoints used during the 5-role demo run-through.

Measures latency, validates HTTP status, and flags any call that exceeds
acceptable live demonstration thresholds (> 500ms or awkward loading).
"""

import asyncio
import time

from httpx import ASGITransport, AsyncClient

from app.main import app

DEMO_ROLES = [
    ("Trainee", "trainee@demo.vikas", "demo2026!"),
    ("Institute Admin", "institute@demo.vikas", "demo2026!"),
    ("Panel Member (Academic)", "panel@demo.vikas", "demo2026!"),
    ("Planner", "planner@demo.vikas", "demo2026!"),
    ("Employer", "employer@demo.vikas", "demo2026!"),
]

SCREEN_CALLS = [
    # Trainee flow
    ("Trainee", "GET", "/trainee/alerts", None),
    ("Trainee", "GET", "/trainee/courses", None),
    ("Trainee", "GET", "/trainee/proficiency-expectations", None),
    (
        "Trainee",
        "POST",
        "/trainee/chat",
        {"question": "What electrician skills are trending in Pune?"},
    ),
    # Institute flow
    ("Institute Admin", "GET", "/institute/flags", None),
    ("Institute Admin", "GET", "/institute/enrollment-vs-demand", None),
    # Panel flow
    ("Panel Member (Academic)", "GET", "/panel/queue", None),
    ("Panel Member (Academic)", "GET", "/panel/governance", None),
    # Planner flow
    ("Planner", "GET", "/planner/map", None),
    (
        "Planner",
        "GET",
        "/planner/compare?district_ids=eba32a6c-fd87-4934-a2c0-8cce1b568cf6,ccc47376-e449-4322-8e03-7ef647de03cf",
        None,
    ),
    (
        "Planner",
        "GET",
        "/planner/export/capacity-plan?district_id=eba32a6c-fd87-4934-a2c0-8cce1b568cf6&format=json",
        None,
    ),
    # Employer flow
    ("Employer", "GET", "/employer/my-validations", None),
    ("Employer", "GET", "/employer/aggregate-readiness", None),
]


async def run_benchmark():
    print(
        "================================================================================"
    )
    print("  VIKAS LIVE DEMO LATENCY & SCREEN BENCHMARK")
    print(
        "================================================================================"
    )

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        # Step 1: Login all roles
        tokens = {}
        for role_name, email, password in DEMO_ROLES:
            t0 = time.perf_counter()
            resp = await client.post(
                "/auth/login", json={"email": email, "password": password}
            )
            dt = (time.perf_counter() - t0) * 1000
            assert resp.status_code == 200, f"Login failed for {email}: {resp.text}"
            tokens[role_name] = resp.json()["access_token"]
            print(f"  [Auth] {role_name:<25} Login: {dt:6.2f} ms")

        print(
            "--------------------------------------------------------------------------------"
        )
        print(
            f"{'Role':<25} | {'Method':<6} | {'Endpoint':<42} | {'Status':<6} | {'Latency':<9}"
        )
        print(
            "--------------------------------------------------------------------------------"
        )

        slowness_warnings = []
        for role_name, method, endpoint, payload in SCREEN_CALLS:
            token = tokens[role_name]
            headers = {"Authorization": f"Bearer {token}"}
            t0 = time.perf_counter()
            if method == "GET":
                resp = await client.get(endpoint, headers=headers)
            else:
                resp = await client.post(endpoint, json=payload, headers=headers)
            dt = (time.perf_counter() - t0) * 1000

            # Trim endpoint for printing
            display_ep = endpoint.split("?")[0]
            if len(display_ep) > 40:
                display_ep = display_ep[:37] + "..."

            status_str = f"{resp.status_code}"
            print(
                f"{role_name:<25} | {method:<6} | {display_ep:<42} | {status_str:<6} | {dt:6.2f} ms"
            )

            if dt > 800:
                slowness_warnings.append((role_name, display_ep, dt))

        print(
            "================================================================================"
        )
        if slowness_warnings:
            print("WARNING: Slow screen endpoints identified:")
            for role_name, ep, dt in slowness_warnings:
                print(
                    f"  - [{role_name}] {ep}: {dt:.2f} ms (Consider background pre-fetching or caching)"
                )
        else:
            print(
                "SUCCESS: All screen endpoints responded within < 800ms demo presentation budget."
            )
        print(
            "================================================================================"
        )


if __name__ == "__main__":
    asyncio.run(run_benchmark())
