"""End-to-end verification script for VIKAS Phase 4 Trainee workflow."""

import asyncio

import httpx

from app.main import app


async def run_walkthrough():
    print("\n" + "=" * 70)
    print("VIKAS PHASE 4: FULL TRAINEE FLOW END-TO-END VERIFICATION")
    print("=" * 70)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        # 1. Login as Trainee
        print("\n[Step 1] Authenticating as Trainee (Pune District)...")
        login_resp = await client.post(
            "/auth/login",
            json={"email": "trainee@dev.vikas", "password": "devpass123"},
        )
        assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
        tokens = login_resp.json()
        token = tokens["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print(" -> Authentication Successful! JWT Access Token received.")

        # Check me endpoint
        me_resp = await client.get("/auth/me", headers=headers)
        user_info = me_resp.json()
        print(
            f" -> Authenticated User: {user_info['full_name']} | Role: {user_info['role']} | District: {user_info['district_id']}"
        )

        # 2. Fetch Trainee District Courses
        print("\n[Step 2] Fetching District Courses (GET /trainee/courses)...")
        courses_resp = await client.get("/trainee/courses", headers=headers)
        assert courses_resp.status_code == 200
        courses = courses_resp.json()
        print(f" -> Received {len(courses)} courses in trainee's district:")

        flagged_course_id = None
        for c in courses:
            raw_scores = [
                k
                for k in ["gap_score", "nlp_confidence", "similarity", "score_breakdown"]
                if k in c
            ]
            assert len(raw_scores) == 0, f"Raw score leaked to trainee: {raw_scores}"
            print(
                f"    • [{c['demand_label'].upper()}] {c['trade_name']} @ {c['institute_name']} "
                f"(Seats: {c['seats_available']} | Status: {c['status']} | Has Alternatives: {c['has_alternatives']})"
            )
            if c["status"] in ("flagged", "obsolete") and not flagged_course_id:
                flagged_course_id = c["id"]

        print(
            " -> AUDIT PASSED: Zero raw numeric scores exposed in course response."
        )

        # 3. Alternatives View for Flagged Course
        if flagged_course_id:
            print(
                f"\n[Step 3] Fetching Alternatives for Flagged Course (GET /trainee/courses/{flagged_course_id}/alternatives)..."
            )
            alt_resp = await client.get(
                f"/trainee/courses/{flagged_course_id}/alternatives",
                headers=headers,
            )
            assert alt_resp.status_code == 200
            alt_data = alt_resp.json()
            print(f" -> Guidance Note: \"{alt_data['guidance_message']}\"")
            print(
                f" -> Recommended Alternatives ({len(alt_data['alternatives'])} courses):"
            )
            for alt in alt_data["alternatives"]:
                print(
                    f"    - {alt['trade_name']} @ {alt['institute_name']} ({alt['demand_label']}): {alt['recommendation_rationale']}"
                )

        # 4. Proficiency Expectations
        if courses:
            first_trade_id = courses[0]["trade_id"]
            print(
                f"\n[Step 4] Fetching Industry Skill Expectations (GET /trainee/proficiency-expectations?trade_id={first_trade_id})..."
            )
            exp_resp = await client.get(
                f"/trainee/proficiency-expectations?trade_id={first_trade_id}",
                headers=headers,
            )
            assert exp_resp.status_code == 200
            exp_data = exp_resp.json()
            print(f" -> Trade: {exp_data['trade_name']} ({exp_data['district_name']})")
            print(
                f" -> Top Priority Hiring Keywords: {', '.join(exp_data['top_in_demand_skills'][:5])}"
            )
            for cat in exp_data["skill_categories"]:
                print(f"    • {cat['category']}: {', '.join(cat['skills'])}")

        # 5. Grounded Chat Assistant
        print("\n[Step 5] Testing Grounded Chat Assistant (POST /trainee/chat)...")
        chat_query = "What electrician training courses and seats are available in Pune?"
        print(f" -> Question: \"{chat_query}\"")
        chat_resp = await client.post(
            "/trainee/chat",
            headers=headers,
            json={"question": chat_query},
        )
        assert chat_resp.status_code == 200
        chat_data = chat_resp.json()
        print(f" -> Assistant Reply: \"{chat_data['reply']}\"")
        print(
            f" -> Provenance: District={chat_data['grounded_district']} | Courses Grounded={chat_data['grounded_courses_count']} | Fallback Used={chat_data['fallback_used']}"
        )

        # 6. Trainee Alerts
        print("\n[Step 6] Checking Trainee Notifications (GET /trainee/alerts)...")
        alerts_resp = await client.get("/trainee/alerts", headers=headers)
        assert alerts_resp.status_code == 200
        alerts = alerts_resp.json()
        print(f" -> Received {len(alerts)} notification(s) for this trainee.")
        for a in alerts[:2]:
            print(
                f"    • [{a['generated_by']}] {a['message']} (Date: {a['created_at']})"
            )

    print("\n" + "=" * 70)
    print("ALL 6 STEPS OF TRAINEE WORKFLOW VERIFIED SUCCESSFULLY!")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    asyncio.run(run_walkthrough())
