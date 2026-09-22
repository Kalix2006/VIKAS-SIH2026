"""Verification script for VIKAS Phase 7: State & District Planner Dashboard.

Demonstrates:
1. Authentication as District Skill Officer / State Planner (planner@dev.vikas).
2. Fetching state map with empirical volume-weighted Alignment Health Index (AHI).
3. District drill-down: Trade-by-trade analytics, enrollment vs demand, divergence scores, and status flags.
4. Multi-district benchmarking: Comparing trade between Pune and another district with divergence delta and in-demand skills.
5. Supervisory override & annotation: Adding supervisory field notes and escalating flag to urgent_escalation.
6. Statutory capacity plan export: Generating structured recommendations in both JSON and CSV formats.
7. Defense-in-depth RBAC: Verifying non-planner roles (trainee) receive HTTP 403 Forbidden on write operations.
"""

import asyncio
import sys

from httpx import ASGITransport, AsyncClient

from app.main import app


async def main():
    print("=" * 80)
    print("VIKAS PHASE 7: STATE & DISTRICT PLANNER PIPELINE VERIFICATION")
    print("=" * 80)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # 1. Login as Planner
        print("\n[Step 1] Authenticating as Planner (planner@dev.vikas)...")
        login_res = await client.post(
            "/auth/login", json={"email": "planner@dev.vikas", "password": "devpass123"}
        )
        if login_res.status_code != 200:
            print(f"FAILED to login as planner: {login_res.text}")
            sys.exit(1)
        planner_token = login_res.json()["access_token"]
        planner_headers = {"Authorization": f"Bearer {planner_token}"}
        print(" -> Planner authenticated successfully.")

        # 2. Fetch Map with AHI
        print("\n[Step 2] Fetching state district map and empirical AHI...")
        map_res = await client.get("/planner/map", headers=planner_headers)
        if map_res.status_code != 200:
            print(f"FAILED to fetch map: {map_res.text}")
            sys.exit(1)
        map_data = map_res.json()
        print(f" -> Total Districts Tracked: {map_data['total_districts']}")
        print(f" -> State Average Health Index: {map_data['state_avg_health']:.1f}/100")
        print(
            f" -> Critical Divergence Districts: {map_data['critical_districts_count']}"
        )
        print(f" -> Formula: {map_data['formula_definition']}")
        for d in map_data["districts"][:5]:
            print(
                f"    * {d['name']} ({d['state']}): AHI={d['alignment_health_score']:.1f}/100 ({d['health_category']}), "
                f"Trades={d['active_trades_count']}, Flags={d['flagged_trades_count']}, Postings={d['total_job_volume']}"
            )

        # Pick Pune district for drilldown
        pune = next(
            (d for d in map_data["districts"] if d["name"] == "Pune"),
            map_data["districts"][0],
        )
        pune_id = pune["id"]

        # 3. District Drilldown
        print(
            f"\n[Step 3] Fetching trade-by-trade analytics for {pune['name']} ({pune_id})..."
        )
        drill_res = await client.get(
            f"/planner/districts/{pune_id}", headers=planner_headers
        )
        if drill_res.status_code != 200:
            print(f"FAILED to fetch district drilldown: {drill_res.text}")
            sys.exit(1)
        drill_data = drill_res.json()
        print(
            f" -> District Health: {drill_data['alignment_health_score']:.1f}/100 ({drill_data['health_category']})"
        )
        print(
            f" -> Total Capacity: {drill_data['total_seats']} seats | Demand Volume: {drill_data['total_postings']} openings"
        )
        print(f" -> Found {len(drill_data['trades'])} trade rows:")
        flagged_gap_id = None
        electrician_trade_id = None
        for t in drill_data["trades"]:
            print(
                f"    * [{t['nsqf_code']}] {t['trade_name']}: Demand={t['job_posting_volume']}, Seats={t['seats_available']}, "
                f"Ratio={t['hiring_to_seats_ratio']:.2f}, Alignment={t['alignment_score']:.1f}, Trend={t['trend_direction']}, Status={t['gap_status']}"
            )
            if t["gap_id"] and not flagged_gap_id:
                flagged_gap_id = t["gap_id"]
            if "electrician" in t["trade_name"].lower():
                electrician_trade_id = t["trade_id"]

        if not electrician_trade_id and drill_data["trades"]:
            electrician_trade_id = drill_data["trades"][0]["trade_id"]

        # 4. Multi-District Comparison
        second_district = next(
            (d for d in map_data["districts"] if d["id"] != pune_id), None
        )
        if second_district and electrician_trade_id:
            print(
                f"\n[Step 4] Benchmarking trade between {pune['name']} and {second_district['name']}..."
            )
            compare_res = await client.get(
                f"/planner/compare?district_ids={pune_id},{second_district['id']}&trade_id={electrician_trade_id}",
                headers=planner_headers,
            )
            if compare_res.status_code != 200:
                print(f"FAILED to benchmark: {compare_res.text}")
                sys.exit(1)
            comp = compare_res.json()
            print(f" -> Benchmarked Trade: {comp['trade_name']} ({comp['nsqf_code']})")
            print(f" -> Alignment Delta: {comp['alignment_score_delta']:.1f} pts")
            print(f" -> Comparative Insight: {comp['comparative_insight']}")
            for cd in [comp["district_a"], comp["district_b"]]:
                print(
                    f"    * {cd['district_name']}: Alignment={cd['alignment_score']:.1f}, Demand={cd['job_posting_volume']}, "
                    f"Seats={cd['seats_available']}, Status={cd['gap_status']}, Top Skills={cd['top_in_demand_skills'][:3]}"
                )

        # 5. Planner Flag Annotation & Status Override
        if flagged_gap_id:
            print(
                f"\n[Step 5] Annotating flagged gap {flagged_gap_id} with override status 'confirmed'..."
            )
            annotate_res = await client.post(
                f"/planner/flags/{flagged_gap_id}/annotate",
                headers=planner_headers,
                json={
                    "note": "Field verification conducted with local auto cluster. Supply deficit confirmed; initiating fast-track curriculum revision.",
                    "override_status": "confirmed",
                },
            )
            if annotate_res.status_code != 200:
                print(f"FAILED to annotate flag: {annotate_res.text}")
                sys.exit(1)
            ann_data = annotate_res.json()
            print(" -> Annotation recorded successfully!")
            print(f'    * Note: "{ann_data["note"]}"')
            print(f"    * Override Status: {ann_data['override_status']}")
            print(f"    * Resulting Gap Status: {ann_data['new_gap_status']}")
            print(f"    * Recorded At: {ann_data['created_at']}")
            assert ann_data["new_gap_status"] == "urgent_escalation", (
                f"Expected urgent_escalation, got {ann_data['new_gap_status']}"
            )
        else:
            print(
                "\n[Step 5] Skipped flag annotation (no flagged gaps found in district)"
            )

        # 6. Structured Capacity Plan Export (JSON and CSV)
        print(f"\n[Step 6] Generating Statutory Capacity Plan for {pune['name']}...")
        # 6a. JSON format
        export_json_res = await client.get(
            f"/planner/export/capacity-plan?district_id={pune_id}&format=json",
            headers=planner_headers,
        )
        if export_json_res.status_code != 200:
            print(f"FAILED to export JSON capacity plan: {export_json_res.text}")
            sys.exit(1)
        plan_json = export_json_res.json()
        print(
            f" -> [JSON] District: {plan_json['district_name']} | Generated: {plan_json['generated_at']}"
        )
        print(
            f"    * Net Seat Adjustment: {plan_json['total_recommended_seat_change']} seats"
        )
        print(
            f"    * Total Trainer Workshops: {plan_json['total_trainer_workshops']} sessions"
        )
        print(f"    * Total Recommendations: {len(plan_json['recommendations'])}")
        for rec in plan_json["recommendations"][:3]:
            print(
                f"       - Trade: {rec['trade_name']} | Seats: {rec['recommended_seat_adjustment']:+d} | Workshops: {rec['recommended_trainer_workshops']} | Priority: {rec['equipment_investment_priority']} ({rec['investment_focus']})"
            )

        # 6b. CSV format
        export_csv_res = await client.get(
            f"/planner/export/capacity-plan?district_id={pune_id}&format=csv",
            headers=planner_headers,
        )
        if export_csv_res.status_code != 200:
            print(f"FAILED to export CSV capacity plan: {export_csv_res.text}")
            sys.exit(1)
        csv_text = export_csv_res.text
        csv_lines = [line for line in csv_text.strip().split("\n") if line]
        print(f" -> [CSV] Header + {len(csv_lines) - 1} data rows exported.")
        print(f"    * Header: {csv_lines[0]}")
        if len(csv_lines) > 1:
            print(f"    * Sample Row: {csv_lines[1]}")

        # 7. Defense-in-depth RBAC check
        print(
            "\n[Step 7] Verifying RBAC defense: Non-planner (trainee) attempting write operation..."
        )
        trainee_login = await client.post(
            "/auth/login", json={"email": "trainee@dev.vikas", "password": "devpass123"}
        )
        trainee_token = trainee_login.json()["access_token"]
        trainee_headers = {"Authorization": f"Bearer {trainee_token}"}

        dummy_flag_id = flagged_gap_id or "00000000-0000-0000-0000-000000000000"
        trainee_write_res = await client.post(
            f"/planner/flags/{dummy_flag_id}/annotate",
            headers=trainee_headers,
            json={"note": "Malicious non-planner write attempt"},
        )
        print(f" -> Trainee write response status: {trainee_write_res.status_code}")
        if trainee_write_res.status_code == 403:
            print(
                " -> [PASS] HTTP 403 Forbidden correctly enforced on non-planner role!"
            )
        else:
            print(
                f" -> [FAIL] Expected HTTP 403, received {trainee_write_res.status_code}"
            )
            sys.exit(1)

    print("\n" + "=" * 80)
    print("ALL PHASE 7 STATE & DISTRICT PLANNER WORKFLOW VERIFICATIONS PASSED!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
