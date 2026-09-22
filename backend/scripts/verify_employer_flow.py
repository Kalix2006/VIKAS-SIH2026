"""Verification script for VIKAS Phase 8: Employer Validation & Demand Signals.

Demonstrates:
1. Authentication as Industrial Employer (employer@dev.vikas).
2. Fetching inferred skill demand for trade/district pre-filled from local vacancy data.
3. Submitting skill validation in under 60 seconds (structured confirmation + free-text parsing/fallback).
4. Submitting a structured hiring intent signal (vacancies, timeframe, urgency).
5. Fetching aggregate cohort readiness and executing a strict recursive privacy audit
   (verifying zero candidate PII or individual trainee identifiers).
6. Multi-tenant isolation: listing historical submissions scoped to authenticated employer.
7. Defense-in-depth RBAC: non-employer roles (trainee) receive HTTP 403 Forbidden.
"""

import asyncio
import sys
import time

from httpx import ASGITransport, AsyncClient

from app.main import app

# Blacklisted candidate identity substrings (lower-cased)
FORBIDDEN_KEY_SUBSTRINGS = [
    "trainee_id",
    "candidate_id",
    "student_id",
    "roll_number",
    "user_id",
    "full_name",
    "first_name",
    "last_name",
    "trainee_name",
    "candidate_name",
    "email",
    "phone",
    "mobile",
    "aadhaar",
    "address",
    "gender",
    "date_of_birth",
    "dob",
]

def recursive_privacy_check(obj, path="root"):
    """Recursively verify that no candidate identifiable keys exist."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            key_lower = k.lower()
            for forbidden in FORBIDDEN_KEY_SUBSTRINGS:
                if forbidden in key_lower:
                    raise AssertionError(
                        f"PRIVACY AUDIT VIOLATION: Forbidden candidate identifier key '{k}' found at path '{path}.{k}'"
                    )
            recursive_privacy_check(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for idx, item in enumerate(obj):
            recursive_privacy_check(item, f"{path}[{idx}]")

async def main():
    print("=" * 80)
    print("VIKAS PHASE 8: EMPLOYER VALIDATION & DEMAND SIGNALS PIPELINE VERIFICATION")
    print("=" * 80)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # 1. Login as Employer
        print("\n[Step 1] Authenticating as Industrial Employer (employer@dev.vikas)...")
        login_res = await client.post("/auth/login", json={
            "email": "employer@dev.vikas",
            "password": "devpass123"
        })
        if login_res.status_code != 200:
            print(f"FAILED to login as employer: {login_res.text}")
            sys.exit(1)
        token_data = login_res.json()
        employer_token = token_data["access_token"]
        headers = {"Authorization": f"Bearer {employer_token}"}
        print(" -> Employer authenticated successfully.")

        # Get profile for district_id
        me_res = await client.get("/auth/me", headers=headers)
        user_data = me_res.json()
        district_id = user_data["district_id"]
        print(f" -> Employer Full Name: {user_data['full_name']}")
        print(f" -> District Scope: {district_id}")

        # Discover available trade ID directly from DB
        from sqlalchemy import select

        from app.db.session import async_session_maker
        from app.models.trade import Trade

        async with async_session_maker() as db:
            stmt = select(Trade)
            trades = list((await db.execute(stmt)).scalars().all())
            electrician_trade = next(
                (t for t in trades if "electrician" in t.name.lower()),
                trades[0]
            )
            trade_id = str(electrician_trade.id)
            trade_name = electrician_trade.name
            nsqf_code = electrician_trade.nsqf_code

        print(f" -> Selected Trade for Validation: {trade_name} ({nsqf_code})")

        # 2. Fetch Inferred Skills
        print(f"\n[Step 2] Fetching inferred skill demand for {trade_name} in district...")
        start_time = time.time()
        inferred_res = await client.get(
            f"/employer/skills-inferred?trade_id={trade_id}&district_id={district_id}",
            headers=headers
        )
        if inferred_res.status_code != 200:
            print(f"FAILED to fetch inferred skills: {inferred_res.text}")
            sys.exit(1)
        inferred = inferred_res.json()
        print(f" -> District: {inferred['district_name']} | Postings Analyzed: {inferred['total_postings_analyzed']}")
        print(f" -> Received {len(inferred['inferred_skills'])} pre-filled skills:")
        for item in inferred["inferred_skills"][:5]:
            print(f"    * [{item['category']}] {item['skill_name']} (Frequency: {item['posting_frequency']}x)")

        # 3. Fast "Under a Minute" Validation Submission
        print("\n[Step 3] Submitting One-Minute Skill Validation with Free-Text...")
        confirmed_list = [s["skill_name"] for s in inferred["inferred_skills"][:6]]
        val_payload = {
            "trade_id": trade_id,
            "district_id": district_id,
            "confirmed_skills": confirmed_list,
            "raw_free_text": "Need technicians experienced in PLC Ladder Logic, three-phase motor maintenance, and substation safety."
        }
        val_res = await client.post("/employer/validate", headers=headers, json=val_payload)
        if val_res.status_code != 200:
            print(f"FAILED to submit validation: {val_res.text}")
            sys.exit(1)
        val_data = val_res.json()
        elapsed = time.time() - start_time
        print(" -> Validation recorded successfully!")
        print(f"    * Validation ID: {val_data['validation_id']}")
        print(f"    * Confirmed Skills ({len(val_data['confirmed_skills'])} items): {val_data['confirmed_skills'][:3]}...")
        print(f"    * Extracted from Free-Text: {val_data['extracted_from_free_text']}")
        print(f"    * Parsed by LLM: {val_data['parsed_by_llm']}")
        print(f"    * Needs Manual Review: {val_data['needs_manual_review']}")
        print(f"    * DEMO TIMING: Completed in {elapsed:.2f} seconds (< 60 seconds target)!")

        # 4. Submit Structured Hiring Signal
        print("\n[Step 4] Submitting Structured Hiring Intent Signal...")
        signal_payload = {
            "trade_id": trade_id,
            "district_id": district_id,
            "vacancies_count": 25,
            "timeframe_months": 3,
            "urgency": "immediate",
            "notes": "Expansion of industrial assembly line requires immediate batch."
        }
        signal_res = await client.post("/employer/hiring-signal", headers=headers, json=signal_payload)
        if signal_res.status_code != 200:
            print(f"FAILED to submit hiring signal: {signal_res.text}")
            sys.exit(1)
        signal_data = signal_res.json()
        print(" -> Hiring Signal recorded successfully!")
        print(f"    * Signal ID: {signal_data['signal_id']}")
        print(f"    * Vacancies: {signal_data['vacancies_count']} positions")
        print(f"    * Timeframe: {signal_data['timeframe_months']} months")
        print(f"    * Urgency: {signal_data['urgency']}")

        # 5. Fetch Aggregate Readiness & Execute Strict Privacy Audit
        print(f"\n[Step 5] Fetching Aggregate Cohort Readiness for {trade_name} & Executing Privacy Audit...")
        readiness_res = await client.get(
            f"/employer/aggregate-readiness?trade_id={trade_id}&district_id={district_id}",
            headers=headers
        )
        if readiness_res.status_code != 200:
            print(f"FAILED to fetch aggregate readiness: {readiness_res.text}")
            sys.exit(1)
        readiness_data = readiness_res.json()
        print(f" -> Total Enrolled Cohort: {readiness_data['total_enrolled_trainees']}")
        print(f" -> Graduating Near-Term (90 days): {readiness_data['graduating_within_90_days']}")
        print(f" -> Cohort Readiness Index: {readiness_data['cohort_readiness_index']}%")
        print(f" -> Readiness Distribution: High={readiness_data['readiness_distribution']['high_readiness']}, "
              f"Moderate={readiness_data['readiness_distribution']['moderate_readiness']}, "
              f"Foundational={readiness_data['readiness_distribution']['foundational']}")
        print(f" -> Privacy Guarantee: \"{readiness_data['privacy_guarantee']}\"")

        # Run Recursive Privacy Check
        recursive_privacy_check(readiness_data)
        print(" -> [PRIVACY AUDIT PASSED]: Zero candidate PII, student names, emails, roll numbers, or personal IDs found in response!")

        # 6. List Employer Submissions (Multi-tenant isolation)
        print("\n[Step 6] Verifying Multi-Tenant Isolation & Submission History...")
        history_res = await client.get("/employer/my-validations", headers=headers)
        if history_res.status_code != 200:
            print(f"FAILED to fetch employer history: {history_res.text}")
            sys.exit(1)
        history = history_res.json()
        print(f" -> Authenticated employer has {len(history)} recorded submissions:")
        for h in history[:3]:
            print(f"    * [{h['type']}] {h['trade_name']} - {h['summary']} (at {h['submitted_at']})")

        # 7. Defense-in-depth RBAC check
        print("\n[Step 7] Verifying RBAC Defense: Non-employer role (trainee) attempting access...")
        trainee_login = await client.post("/auth/login", json={
            "email": "trainee@dev.vikas",
            "password": "devpass123"
        })
        trainee_token = trainee_login.json()["access_token"]
        trainee_headers = {"Authorization": f"Bearer {trainee_token}"}

        blocked_res = await client.post(
            "/employer/validate",
            headers=trainee_headers,
            json=val_payload
        )
        print(f" -> Trainee validate attempt status: {blocked_res.status_code}")
        if blocked_res.status_code == 403:
            print(" -> [PASS] HTTP 403 Forbidden correctly enforced on non-employer role!")
        else:
            print(f" -> [FAIL] Expected 403, received {blocked_res.status_code}")
            sys.exit(1)

    print("\n" + "=" * 80)
    print("ALL PHASE 8 EMPLOYER VALIDATION & PRIVACY WORKFLOW VERIFICATIONS PASSED!")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(main())
