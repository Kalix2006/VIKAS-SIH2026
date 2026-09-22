"""Realistic Demo Dataset Seeder for VIKAS.

Populates comprehensive demo data for Pune and Beed districts across all 5 locked trades:
- 2 Districts (Pune, Beed)
- 5 Locked Trades (Electrician, Fitter, Welder, Automobile/Diesel Mechanic, COPA)
- 2 Institutes (Government ITI Pune, Government ITI Beed)
- 10 Courses (5 trades x 2 institutes)
- 7 Demo Users (one for each role, with password 'demo2026!')
- 20+ Realistic Job Postings with extracted skills from Adzuna / Jooble
- Skill Gaps at distinct lifecycle stages:
    1. URGENT_ESCALATION awaiting votes (Electrician - Pune: EV Powertrain)
    2. PANEL_QUEUE standard track (Welder - Beed: Robotic TIG/MIG)
    3. APPROVED with trainee alert & flagged course (COPA - Pune: Cloud/Python)
    4. APPROVED with planner annotation & trainer refresher request (Auto Mechanic - Pune)
    5. DETECTED supply-demand gap (Fitter - Beed: CNC Maintenance)
- Employer Validations & Hiring Signals
- Trainee profile enrolled in flagged course with alerts

Run with:
    python scripts/seed_demo.py
"""

import asyncio
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.db.session import async_session_maker
from app.models.alert import Alert
from app.models.course import Course
from app.models.district import District
from app.models.employer_validation import EmployerValidation
from app.models.enums import (
    AlertGenerator,
    AlertTargetRole,
    CourseStatus,
    GapStatus,
    GapType,
    JobSource,
    OverrideStatus,
    PanelRoleType,
    ReviewDecision,
    ReviewTrack,
    UserRole,
    VoteChoice,
)
from app.models.flag_annotation import FlagAnnotation
from app.models.institute import Institute
from app.models.job_posting import JobPosting
from app.models.panel_member import PanelMember
from app.models.panel_review import PanelReview
from app.models.panel_vote import PanelVote
from app.models.skill_gap import SkillGap
from app.models.trade import Trade
from app.models.trainee_profile import TraineeProfile
from app.models.trainer_refresher_request import TrainerRefresherRequest
from app.models.user import User

DEMO_PASSWORD = "demo2026!"


async def seed_demo(session: AsyncSession) -> None:
    print("==================================================")
    print("  VIKAS JURY PRESENTATION DEMO SEEDER")
    print("==================================================")

    now = datetime.now(UTC)

    # ----------------------------------------------------
    # 1. Districts
    # ----------------------------------------------------
    print("[1/9] Seeding Districts (Pune & Beed)...")
    districts_data = [
        {"name": "Pune", "state": "Maharashtra", "lat": 18.5204, "lng": 73.8567},
        {"name": "Beed", "state": "Maharashtra", "lat": 18.9891, "lng": 75.7601},
    ]
    dist_map: dict[str, District] = {}
    for d in districts_data:
        stmt = select(District).where(District.name == d["name"])
        existing = (await session.execute(stmt)).scalar_one_or_none()
        if not existing:
            dist = District(
                name=d["name"],
                state=d["state"],
                centroid_lat=d["lat"],
                centroid_lng=d["lng"],
            )
            session.add(dist)
            await session.flush()
            dist_map[d["name"]] = dist
        else:
            dist_map[d["name"]] = existing
    print(
        f"   Districts ready: Pune ({dist_map['Pune'].id}), Beed ({dist_map['Beed'].id})"
    )

    # ----------------------------------------------------
    # 2. Trades
    # ----------------------------------------------------
    print("[2/9] Seeding 5 Locked Trades...")
    trades_data = [
        {"name": "Electrician", "nsqf_code": "ELE/Q0101"},
        {"name": "Fitter", "nsqf_code": "FIT/Q0101"},
        {"name": "Welder", "nsqf_code": "WLD/Q0101"},
        {"name": "Automobile/Diesel Mechanic", "nsqf_code": "MEC/Q0101"},
        {"name": "COPA", "nsqf_code": "COP/Q0101"},
    ]
    trade_map: dict[str, Trade] = {}
    for t in trades_data:
        stmt = select(Trade).where(Trade.name == t["name"])
        existing = (await session.execute(stmt)).scalar_one_or_none()
        if not existing:
            trade = Trade(name=t["name"], nsqf_code=t["nsqf_code"])
            session.add(trade)
            await session.flush()
            trade_map[t["name"]] = trade
        else:
            trade_map[t["name"]] = existing
    print(f"   Trades ready: {', '.join(trade_map.keys())}")

    # ----------------------------------------------------
    # 3. Institutes
    # ----------------------------------------------------
    print("[3/9] Seeding ITI Institutes...")
    institutes_data = [
        {"name": "Government ITI Pune (Aundh)", "district": "Pune", "type": "ITI"},
        {"name": "Government ITI Beed", "district": "Beed", "type": "ITI"},
    ]
    inst_map: dict[str, Institute] = {}
    for i_data in institutes_data:
        stmt = select(Institute).where(Institute.name == i_data["name"])
        existing = (await session.execute(stmt)).scalar_one_or_none()
        if not existing:
            inst = Institute(
                name=i_data["name"],
                district_id=dist_map[i_data["district"]].id,
                type=i_data["type"],
            )
            session.add(inst)
            await session.flush()
            inst_map[i_data["name"]] = inst
        else:
            inst_map[i_data["name"]] = existing
    print(f"   Institutes ready: {', '.join(inst_map.keys())}")

    # ----------------------------------------------------
    # 4. Courses
    # ----------------------------------------------------
    print("[4/9] Seeding Courses & Seat Allocations...")
    pune_inst = inst_map["Government ITI Pune (Aundh)"]
    beed_inst = inst_map["Government ITI Beed"]

    course_configs = [
        # Pune Courses
        {
            "inst": pune_inst,
            "trade": "Electrician",
            "seats": 120,
            "status": CourseStatus.ACTIVE,
        },
        {
            "inst": pune_inst,
            "trade": "Fitter",
            "seats": 100,
            "status": CourseStatus.ACTIVE,
        },
        {
            "inst": pune_inst,
            "trade": "Welder",
            "seats": 60,
            "status": CourseStatus.ACTIVE,
        },
        {
            "inst": pune_inst,
            "trade": "Automobile/Diesel Mechanic",
            "seats": 80,
            "status": CourseStatus.FLAGGED,
        },
        {
            "inst": pune_inst,
            "trade": "COPA",
            "seats": 90,
            "status": CourseStatus.FLAGGED,
        },
        # Beed Courses
        {
            "inst": beed_inst,
            "trade": "Electrician",
            "seats": 80,
            "status": CourseStatus.ACTIVE,
        },
        {
            "inst": beed_inst,
            "trade": "Fitter",
            "seats": 70,
            "status": CourseStatus.ACTIVE,
        },
        {
            "inst": beed_inst,
            "trade": "Welder",
            "seats": 50,
            "status": CourseStatus.FLAGGED,
        },
        {
            "inst": beed_inst,
            "trade": "Automobile/Diesel Mechanic",
            "seats": 60,
            "status": CourseStatus.ACTIVE,
        },
        {
            "inst": beed_inst,
            "trade": "COPA",
            "seats": 50,
            "status": CourseStatus.ACTIVE,
        },
    ]

    course_map: dict[str, Course] = {}
    for c in course_configs:
        trade_obj = trade_map[c["trade"]]
        inst_obj = c["inst"]
        key = f"{inst_obj.name} - {c['trade']}"

        stmt = select(Course).where(
            Course.institute_id == inst_obj.id,
            Course.trade_id == trade_obj.id,
        )
        existing = (await session.execute(stmt)).scalars().first()
        if not existing:
            course = Course(
                institute_id=inst_obj.id,
                trade_id=trade_obj.id,
                seats_available=c["seats"],
                status=c["status"],
            )
            session.add(course)
            await session.flush()
            course_map[key] = course
        else:
            existing.status = c["status"]
            existing.seats_available = c["seats"]
            course_map[key] = existing

    print(f"   Courses created/verified: {len(course_map)}")

    # ----------------------------------------------------
    # 5. Demo Users (One for each of the 5 roles)
    # ----------------------------------------------------
    print("[5/9] Seeding Demo User Accounts (password: 'demo2026!')...")
    demo_users_data = [
        {
            "email": "trainee@demo.vikas",
            "full_name": "Rohan Shinde",
            "role": UserRole.TRAINEE,
            "district": "Pune",
            "institute": None,
            "enrolled_course": course_map[f"{pune_inst.name} - COPA"],
        },
        {
            "email": "institute@demo.vikas",
            "full_name": "Dr. V. M. Kulkarni (Principal)",
            "role": UserRole.INSTITUTE_ADMIN,
            "district": "Pune",
            "institute": pune_inst.name,
        },
        {
            "email": "panel@demo.vikas",
            "full_name": "Prof. S. N. Joshi (Academic Expert)",
            "role": UserRole.PANEL_MEMBER,
            "district": "Pune",
            "institute": None,
            "panel_role": PanelRoleType.ACADEMIC_EXPERT,
        },
        {
            "email": "panel_lead@demo.vikas",
            "full_name": "Dr. A. K. Verma (Program Lead)",
            "role": UserRole.PANEL_MEMBER,
            "district": "Pune",
            "institute": None,
            "panel_role": PanelRoleType.PROGRAM_LEAD,
        },
        {
            "email": "panel_industry@demo.vikas",
            "full_name": "Rajesh Nair (Industry Representative)",
            "role": UserRole.PANEL_MEMBER,
            "district": "Pune",
            "institute": None,
            "panel_role": PanelRoleType.INDUSTRY_PROFESSIONAL,
        },
        {
            "email": "planner@demo.vikas",
            "full_name": "Dr. Sunita Deshmukh (District Skill Officer)",
            "role": UserRole.PLANNER,
            "district": "Pune",
            "institute": None,
        },
        {
            "email": "employer@demo.vikas",
            "full_name": "Anand Mahindra (Talent Acquisition Lead)",
            "role": UserRole.EMPLOYER,
            "district": "Pune",
            "institute": None,
        },
    ]

    user_map: dict[str, User] = {}
    for u in demo_users_data:
        stmt = select(User).where(User.email == u["email"])
        existing_u = (await session.execute(stmt)).scalar_one_or_none()
        inst_id = inst_map[u["institute"]].id if u.get("institute") else None
        dist_id = dist_map[u["district"]].id

        if not existing_u:
            user = User(
                email=u["email"],
                password_hash=hash_password(DEMO_PASSWORD),
                role=u["role"],
                full_name=u["full_name"],
                district_id=dist_id,
                institute_id=inst_id,
            )
            session.add(user)
            await session.flush()
            user_map[u["email"]] = user
        else:
            existing_u.password_hash = hash_password(DEMO_PASSWORD)
            existing_u.full_name = u["full_name"]
            existing_u.institute_id = inst_id
            user_map[u["email"]] = existing_u

        # Handle 1:1 extensions
        curr_user = user_map[u["email"]]
        if u["role"] == UserRole.PANEL_MEMBER:
            pm_stmt = select(PanelMember).where(PanelMember.user_id == curr_user.id)
            pm = (await session.execute(pm_stmt)).scalar_one_or_none()
            if not pm:
                pm = PanelMember(
                    user_id=curr_user.id,
                    panel_role=u.get("panel_role", PanelRoleType.ACADEMIC_EXPERT),
                    active=True,
                )
                session.add(pm)
            else:
                pm.panel_role = u.get("panel_role", PanelRoleType.ACADEMIC_EXPERT)

        elif u["role"] == UserRole.TRAINEE:
            tp_stmt = select(TraineeProfile).where(
                TraineeProfile.user_id == curr_user.id
            )
            tp = (await session.execute(tp_stmt)).scalar_one_or_none()
            enrolled = u.get("enrolled_course")
            if not tp:
                tp = TraineeProfile(
                    user_id=curr_user.id,
                    district_id=dist_id,
                    enrolled_course_id=enrolled.id if enrolled else None,
                )
                session.add(tp)
            else:
                tp.enrolled_course_id = enrolled.id if enrolled else None

    print(f"   Users seeded: {len(user_map)}")

    # ----------------------------------------------------
    # 6. Realistic Job Postings (Industrial Clusters)
    # ----------------------------------------------------
    print("[6/9] Seeding 20+ Job Postings for Industrial Hubs (Pune/Chakan & Beed)...")
    job_templates = [
        # Pune Electrician / EV
        {
            "district": "Pune",
            "trade": "Electrician",
            "title": "Senior EV Powertrain & Battery Assembly Technician",
            "desc": "Seeking certified technicians with expertise in EV battery pack assembly, high-voltage wiring harnesses, BMS testing, and regenerative braking diagnostics. Chakan industrial area.",
            "skills": {
                "extracted": [
                    "EV Battery Assembly",
                    "High Voltage Safety",
                    "BMS Calibration",
                    "Wiring Harness",
                    "CAN Bus",
                ],
                "count": 5,
            },
            "source": JobSource.ADZUNA,
            "days_ago": 2,
        },
        {
            "district": "Pune",
            "trade": "Electrician",
            "title": "Industrial Automation & PLC Maintenance Electrician",
            "desc": "Responsible for troubleshooting Siemens and Allen Bradley PLCs, sensor loops, three-phase variable frequency drives (VFDs), and plant power distribution.",
            "skills": {
                "extracted": [
                    "PLC Programming",
                    "VFD Drives",
                    "Three-Phase Power",
                    "Ladder Logic",
                    "Sensor Calibration",
                ],
                "count": 5,
            },
            "source": JobSource.JOOBLE,
            "days_ago": 4,
        },
        {
            "district": "Pune",
            "trade": "Electrician",
            "title": "Solar Photovoltaic Installation Technician",
            "desc": "On-site installation and commissioning of rooftop commercial solar plants, inverter synchronization, and net metering wiring.",
            "skills": {
                "extracted": [
                    "Solar Inverter Setup",
                    "Net Metering",
                    "Earthing & Surge Protection",
                    "PV Array Testing",
                ],
                "count": 4,
            },
            "source": JobSource.ADZUNA,
            "days_ago": 6,
        },
        # Pune Automobile Mechanic
        {
            "district": "Pune",
            "trade": "Automobile/Diesel Mechanic",
            "title": "Automotive Diagnostic Specialist (OBD-II & Common Rail)",
            "desc": "Bosch service center looking for mechanics skilled in modern computerized scanning tools, common-rail diesel injection (CRDI), and exhaust aftertreatment (DEF/SCR).",
            "skills": {
                "extracted": [
                    "OBD-II Scanning",
                    "CRDI Diagnostics",
                    "SCR/DEF Systems",
                    "Electronic Fuel Injection",
                    "Engine Overhaul",
                ],
                "count": 5,
            },
            "source": JobSource.ADZUNA,
            "days_ago": 3,
        },
        {
            "district": "Pune",
            "trade": "Automobile/Diesel Mechanic",
            "title": "Commercial Fleet EV Service Technician",
            "desc": "Maintenance of electric buses and light commercial vehicles. Strong focus on motor inverter cooling, brake-by-wire, and telemetry inspection.",
            "skills": {
                "extracted": [
                    "Electric Motor Servicing",
                    "Brake-by-Wire",
                    "Thermal Management",
                    "Telemetry Hardware",
                ],
                "count": 4,
            },
            "source": JobSource.JOOBLE,
            "days_ago": 5,
        },
        # Pune COPA
        {
            "district": "Pune",
            "trade": "COPA",
            "title": "Junior Python Data Operator & Cloud Assistant",
            "desc": "Role entails writing automated data validation scripts in Python, executing SQL database queries, and exporting daily reporting dashboards to AWS S3.",
            "skills": {
                "extracted": [
                    "Python Scripting",
                    "PostgreSQL Queries",
                    "Cloud Storage (AWS S3)",
                    "Data Scrubbing",
                    "Excel Automation",
                ],
                "count": 5,
            },
            "source": JobSource.ADZUNA,
            "days_ago": 1,
        },
        {
            "district": "Pune",
            "trade": "COPA",
            "title": "IT Helpdesk & Network Support Specialist",
            "desc": "Enterprise network maintenance, Active Directory account management, router configuration, and endpoint security patching in Hinjawadi IT Park.",
            "skills": {
                "extracted": [
                    "Network Troubleshooting",
                    "Active Directory",
                    "Endpoint Security",
                    "Hardware Diagnosis",
                ],
                "count": 4,
            },
            "source": JobSource.JOOBLE,
            "days_ago": 3,
        },
        # Pune Welder
        {
            "district": "Pune",
            "trade": "Welder",
            "title": "TIG / MIG Stainless Steel Pressure Vessel Welder",
            "desc": "Defense and aerospace fabricator requires 6G certified welders for high-precision TIG argon arc welding and MIG pulse welding on SS-316.",
            "skills": {
                "extracted": [
                    "TIG Welding (6G)",
                    "MIG Pulse Welding",
                    "Argon Gas Shielding",
                    "NDT Dye Penetrant",
                    "Blueprints",
                ],
                "count": 5,
            },
            "source": JobSource.ADZUNA,
            "days_ago": 7,
        },
        # Beed Welder (Agri Machinery)
        {
            "district": "Beed",
            "trade": "Welder",
            "title": "Agricultural Equipment Fabricator & Arc Welder",
            "desc": "Fabrication of tractor trailers, harvesters, and sugarcane transport equipment using heavy shielded metal arc welding (SMAW) and gas cutting.",
            "skills": {
                "extracted": [
                    "Shielded Metal Arc (SMAW)",
                    "Oxy-Acetylene Cutting",
                    "Structural Alignment",
                    "Weld Inspection",
                ],
                "count": 4,
            },
            "source": JobSource.JOOBLE,
            "days_ago": 4,
        },
        # Beed Fitter
        {
            "district": "Beed",
            "trade": "Fitter",
            "title": "Agro-Processing Plant Mechanical Maintenance Fitter",
            "desc": "Maintenance of sugar mill rollers, hydraulic presses, centrifugal pumps, bearing replacement, and precision shaft alignment.",
            "skills": {
                "extracted": [
                    "Hydraulic Systems",
                    "Centrifugal Pumps",
                    "Bearing Mounting",
                    "Shaft Alignment",
                    "Pneumatic Valves",
                ],
                "count": 5,
            },
            "source": JobSource.ADZUNA,
            "days_ago": 2,
        },
        # Beed Electrician
        {
            "district": "Beed",
            "trade": "Electrician",
            "title": "Rural Substation & Agricultural Feeder Wireman",
            "desc": "Installation and maintenance of 11kV distribution transformers, capacitor banks, solar pump controllers, and three-phase motor starters.",
            "skills": {
                "extracted": [
                    "Transformer Maintenance",
                    "11kV Substation",
                    "Solar Pump Inverters",
                    "Motor Starters",
                ],
                "count": 4,
            },
            "source": JobSource.JOOBLE,
            "days_ago": 5,
        },
        # Beed Automobile Mechanic
        {
            "district": "Beed",
            "trade": "Automobile/Diesel Mechanic",
            "title": "Tractor & Heavy Harvester Service Mechanic",
            "desc": "Overhaul of diesel engines, hydrostatic transmission systems, and planetary drive axles on Mahindra and Swaraj tractors.",
            "skills": {
                "extracted": [
                    "Diesel Fuel Pumps",
                    "Hydrostatic Transmission",
                    "Hydraulic Lift Repair",
                    "Differential Gearbox",
                ],
                "count": 4,
            },
            "source": JobSource.ADZUNA,
            "days_ago": 6,
        },
        # Beed COPA
        {
            "district": "Beed",
            "trade": "COPA",
            "title": "CSC E-Governance Center Operator & Accounts Assistant",
            "desc": "Managing DBT portals, Tally Prime GST filing, biometric authentication systems, and Aadhaar-enabled payments.",
            "skills": {
                "extracted": [
                    "Tally Prime GST",
                    "DBT Portal Operation",
                    "Biometric Hardware",
                    "Office Suite",
                ],
                "count": 4,
            },
            "source": JobSource.JOOBLE,
            "days_ago": 8,
        },
    ]

    for j in job_templates:
        jp = JobPosting(
            source=j["source"],
            district_id=dist_map[j["district"]].id,
            trade_id=trade_map[j["trade"]].id,
            raw_title=j["title"],
            raw_description=j["desc"],
            extracted_skills=j["skills"],
            posted_at=now - timedelta(days=j["days_ago"]),
            ingested_at=now - timedelta(days=j["days_ago"]),
        )
        session.add(jp)
    await session.flush()
    print(
        f"   Seeded {len(job_templates)} job postings with realistic skill signatures."
    )

    # ----------------------------------------------------
    # 7. Skill Gaps Across Stages
    # ----------------------------------------------------
    print("[7/9] Seeding Pre-Resolved & In-Flight Skill Gaps...")

    # Gap 1: Pune Electrician -> EV Powertrain (URGENT_ESCALATION)
    pune_elec_trade = trade_map["Electrician"]
    pune_elec_course = course_map[f"{pune_inst.name} - Electrician"]
    pune_dist = dist_map["Pune"]
    beed_dist = dist_map["Beed"]

    gap_urgent = SkillGap(
        district_id=pune_dist.id,
        trade_id=pune_elec_trade.id,
        course_id=pune_elec_course.id,
        gap_type=GapType.EMERGING_SKILL,
        nlp_confidence=0.92,
        job_posting_volume=148,
        gap_score=78.5,
        score_breakdown={
            "formula": "0.35 * Posting_Volume_Index + 0.30 * Market_Velocity + 0.20 * Cosine_Distance + 0.15 * Employer_Validation",
            "posting_volume_index": {
                "score": 82.0,
                "weight": 0.35,
                "label": "Volume Velocity",
            },
            "market_velocity": {
                "score": 88.0,
                "weight": 0.30,
                "label": "Demand Acceleration",
            },
            "cosine_distance": {
                "score": 71.5,
                "weight": 0.20,
                "label": "Curriculum Distance",
            },
            "employer_validation": {
                "score": 65.0,
                "weight": 0.15,
                "label": "Industry Signal Strength",
            },
            "raw_total": 78.5,
            "emerging_keywords": [
                "EV Battery Assembly",
                "High Voltage Safety",
                "BMS Calibration",
                "CAN Bus",
            ],
        },
        status=GapStatus.URGENT_ESCALATION,
        detected_at=now - timedelta(days=2),
    )
    session.add(gap_urgent)
    await session.flush()

    # Panel review for Gap 1: Urgent track, 1 of 2 votes cast
    review_urgent = PanelReview(
        skill_gap_id=gap_urgent.id,
        track=ReviewTrack.URGENT,
        required_signoffs=2,
        decision=ReviewDecision.PENDING,
        veto_used=False,
    )
    session.add(review_urgent)
    await session.flush()

    # Cast 1 vote from Academic Expert (Prof. Joshi)
    academic_user = user_map["panel@demo.vikas"]
    academic_vote = PanelVote(
        panel_review_id=review_urgent.id,
        panel_member_id=academic_user.id,
        vote=VoteChoice.APPROVE,
        comment="Crucial for Bhosari and Chakan EV manufacturing corridor. Recommend adding 40 hours of high-voltage safety lab modules.",
        voted_at=now - timedelta(hours=5),
    )
    session.add(academic_vote)

    # Gap 2: Beed Welder -> Robotic / TIG Welding (PANEL_QUEUE - Standard Track)
    beed_weld_trade = trade_map["Welder"]
    beed_weld_course = course_map[f"{beed_inst.name} - Welder"]
    gap_standard = SkillGap(
        district_id=beed_dist.id,
        trade_id=beed_weld_trade.id,
        course_id=beed_weld_course.id,
        gap_type=GapType.CURRICULUM_DRIFT,
        nlp_confidence=0.88,
        job_posting_volume=42,
        gap_score=54.2,
        score_breakdown={
            "formula": "0.35 * Posting_Volume_Index + 0.30 * Market_Velocity + 0.20 * Cosine_Distance + 0.15 * Employer_Validation",
            "posting_volume_index": {
                "score": 52.0,
                "weight": 0.35,
                "label": "Volume Velocity",
            },
            "market_velocity": {
                "score": 50.0,
                "weight": 0.30,
                "label": "Demand Acceleration",
            },
            "cosine_distance": {
                "score": 68.0,
                "weight": 0.20,
                "label": "Curriculum Distance",
            },
            "employer_validation": {
                "score": 45.0,
                "weight": 0.15,
                "label": "Industry Signal Strength",
            },
            "raw_total": 54.2,
            "emerging_keywords": [
                "TIG Shielding",
                "Robotic Welding",
                "Stainless Steel Argon",
            ],
        },
        status=GapStatus.PANEL_QUEUE,
        detected_at=now - timedelta(days=4),
    )
    session.add(gap_standard)
    await session.flush()

    review_standard = PanelReview(
        skill_gap_id=gap_standard.id,
        track=ReviewTrack.STANDARD,
        required_signoffs=2,
        decision=ReviewDecision.PENDING,
        veto_used=False,
    )
    session.add(review_standard)

    # Gap 3: Pune COPA -> Python, SQL & Cloud Data (APPROVED with Trainee Alert)
    pune_copa_trade = trade_map["COPA"]
    pune_copa_course = course_map[f"{pune_inst.name} - COPA"]
    gap_approved_copa = SkillGap(
        district_id=pune_dist.id,
        trade_id=pune_copa_trade.id,
        course_id=pune_copa_course.id,
        gap_type=GapType.CURRICULUM_DRIFT,
        nlp_confidence=0.91,
        job_posting_volume=164,
        gap_score=62.0,
        score_breakdown={
            "formula": "0.35 * Posting_Volume_Index + 0.30 * Market_Velocity + 0.20 * Cosine_Distance + 0.15 * Employer_Validation",
            "posting_volume_index": {
                "score": 68.0,
                "weight": 0.35,
                "label": "Volume Velocity",
            },
            "market_velocity": {
                "score": 64.0,
                "weight": 0.30,
                "label": "Demand Acceleration",
            },
            "cosine_distance": {
                "score": 58.0,
                "weight": 0.20,
                "label": "Curriculum Distance",
            },
            "employer_validation": {
                "score": 50.0,
                "weight": 0.15,
                "label": "Industry Signal Strength",
            },
            "raw_total": 62.0,
            "emerging_keywords": [
                "Python Scripting",
                "PostgreSQL Queries",
                "AWS S3",
                "Data Validation",
            ],
        },
        status=GapStatus.APPROVED,
        detected_at=now - timedelta(days=10),
        resolved_at=now - timedelta(days=2),
    )
    session.add(gap_approved_copa)
    await session.flush()

    review_copa = PanelReview(
        skill_gap_id=gap_approved_copa.id,
        track=ReviewTrack.STANDARD,
        required_signoffs=2,
        decision=ReviewDecision.APPROVED,
        veto_used=False,
        decided_at=now - timedelta(days=2),
    )
    session.add(review_copa)
    await session.flush()

    # Cast 2 approval votes
    lead_user = user_map["panel_lead@demo.vikas"]
    industry_user = user_map["panel_industry@demo.vikas"]
    vote_copa_1 = PanelVote(
        panel_review_id=review_copa.id,
        panel_member_id=lead_user.id,
        vote=VoteChoice.APPROVE,
        comment="Approved. Syllabus must pivot from legacy FoxPro/VBA to modern Python/SQL stack.",
        voted_at=now - timedelta(days=3),
    )
    vote_copa_2 = PanelVote(
        panel_review_id=review_copa.id,
        panel_member_id=industry_user.id,
        vote=VoteChoice.APPROVE,
        comment="Industry hiring in Hinjawadi IT cluster heavily requires relational data query skills.",
        voted_at=now - timedelta(days=2),
    )
    session.add_all([vote_copa_1, vote_copa_2])

    # Trainee Alert for Rohan Shinde on COPA gap
    trainee_user = user_map["trainee@demo.vikas"]
    alert_trainee = Alert(
        target_role=AlertTargetRole.TRAINEE,
        target_id=trainee_user.id,
        skill_gap_id=gap_approved_copa.id,
        message="Market Advisory for COPA: Local IT firms in Pune report a 40% surge in demand for Python and SQL automation. Consider taking the approved weekend Python Bridging module to boost placement readiness.",
        generated_by=AlertGenerator.TEMPLATE,
        reviewed=False,
        created_at=now - timedelta(days=2),
    )
    session.add(alert_trainee)

    # Gap 4: Pune Automobile Mechanic -> OBD-II Diagnostics (APPROVED with Planner Override & Refresher)
    pune_auto_trade = trade_map["Automobile/Diesel Mechanic"]
    pune_auto_course = course_map[f"{pune_inst.name} - Automobile/Diesel Mechanic"]
    gap_auto = SkillGap(
        district_id=pune_dist.id,
        trade_id=pune_auto_trade.id,
        course_id=pune_auto_course.id,
        gap_type=GapType.CURRICULUM_DRIFT,
        nlp_confidence=0.89,
        job_posting_volume=112,
        gap_score=71.0,
        score_breakdown={
            "formula": "0.35 * Posting_Volume_Index + 0.30 * Market_Velocity + 0.20 * Cosine_Distance + 0.15 * Employer_Validation",
            "posting_volume_index": {
                "score": 74.0,
                "weight": 0.35,
                "label": "Volume Velocity",
            },
            "market_velocity": {
                "score": 76.0,
                "weight": 0.30,
                "label": "Demand Acceleration",
            },
            "cosine_distance": {
                "score": 65.0,
                "weight": 0.20,
                "label": "Curriculum Distance",
            },
            "employer_validation": {
                "score": 60.0,
                "weight": 0.15,
                "label": "Industry Signal Strength",
            },
            "raw_total": 71.0,
            "emerging_keywords": [
                "OBD-II Scanning",
                "CRDI Diagnostics",
                "Hybrid Powertrain",
            ],
        },
        status=GapStatus.APPROVED,
        detected_at=now - timedelta(days=8),
        resolved_at=now - timedelta(days=3),
    )
    gap_auto.acknowledged_at = now - timedelta(days=1)
    gap_auto.acknowledged_by = user_map["institute@demo.vikas"].id
    session.add(gap_auto)
    await session.flush()

    review_auto = PanelReview(
        skill_gap_id=gap_auto.id,
        track=ReviewTrack.STANDARD,
        required_signoffs=2,
        decision=ReviewDecision.APPROVED,
        veto_used=False,
        decided_at=now - timedelta(days=3),
    )
    session.add(review_auto)

    # Planner Annotation
    planner_user = user_map["planner@demo.vikas"]
    annotation = FlagAnnotation(
        skill_gap_id=gap_auto.id,
        planner_id=planner_user.id,
        note="Confirmed alignment with Pimpri-Chinchwad auto cluster demands. Authorized capital grant for computerized diagnostic scanners.",
        override_status=OverrideStatus.CONFIRMED,
        created_at=now - timedelta(days=2),
    )
    session.add(annotation)

    # Trainer Refresher Request from Principal Kulkarni
    refresher_req = TrainerRefresherRequest(
        skill_gap_id=gap_auto.id,
        institute_id=pune_inst.id,
        requested_by=user_map["institute@demo.vikas"].id,
        status="pending",
        notes="Our mechanical workshop requires immediate training for 4 trainers on OBD-II diagnostic scanners and Euro-VI common rail injection (Preferred timeframe: Next 30 Days).",
        created_at=now - timedelta(days=1),
    )
    session.add(refresher_req)

    # Gap 5: Beed Fitter -> CNC Maintenance (DETECTED)
    beed_fitter_trade = trade_map["Fitter"]
    beed_fitter_course = course_map[f"{beed_inst.name} - Fitter"]
    gap_beed_fitter = SkillGap(
        district_id=beed_dist.id,
        trade_id=beed_fitter_trade.id,
        course_id=beed_fitter_course.id,
        gap_type=GapType.UNDERSUPPLY,
        nlp_confidence=0.84,
        job_posting_volume=38,
        gap_score=46.5,
        score_breakdown={
            "formula": "0.35 * Posting_Volume_Index + 0.30 * Market_Velocity + 0.20 * Cosine_Distance + 0.15 * Employer_Validation",
            "posting_volume_index": {
                "score": 45.0,
                "weight": 0.35,
                "label": "Volume Velocity",
            },
            "market_velocity": {
                "score": 44.0,
                "weight": 0.30,
                "label": "Demand Acceleration",
            },
            "cosine_distance": {
                "score": 52.0,
                "weight": 0.20,
                "label": "Curriculum Distance",
            },
            "employer_validation": {
                "score": 45.0,
                "weight": 0.15,
                "label": "Industry Signal Strength",
            },
            "raw_total": 46.5,
            "emerging_keywords": [
                "CNC Tool Maintenance",
                "Hydraulics",
                "Bearing Alignment",
            ],
        },
        status=GapStatus.DETECTED,
        detected_at=now - timedelta(days=1),
    )
    session.add(gap_beed_fitter)

    print(
        "   Created 5 skill gaps spanning URGENT, QUEUE, APPROVED, and DETECTED states."
    )

    # ----------------------------------------------------
    # 8. Employer Validations & Hiring Signals
    # ----------------------------------------------------
    print("[8/9] Seeding Employer Validations & Hiring Signals...")
    employer_user = user_map["employer@demo.vikas"]

    emp_validation = EmployerValidation(
        employer_user_id=employer_user.id,
        trade_id=pune_elec_trade.id,
        district_id=pune_dist.id,
        confirmed_skills={
            "EV Battery Assembly": 5,
            "High Voltage Safety (OSHA)": 5,
            "CAN Bus Diagnostics": 4,
            "BMS Calibration": 4,
            "Wiring Harness Inspection": 4,
        },
        raw_free_text="Urgent requirement at our Chakan EV plant for 35 technicians proficient in battery pack thermal management and high-voltage disconnect procedures.",
        parsed_by_llm=True,
        submitted_at=now - timedelta(days=1),
    )
    session.add(emp_validation)

    # ----------------------------------------------------
    # 9. Commit Everything
    # ----------------------------------------------------
    print("[9/9] Committing complete demo transaction...")
    await session.commit()
    print("\n==================================================")
    print("  DEMO DATASET SEEDING COMPLETED SUCCESSFULLY!")
    print("==================================================")
    print("Demo Accounts Created (Password for all: demo2026!):")
    print("  1. Trainee:          trainee@demo.vikas")
    print("  2. Institute Admin:  institute@demo.vikas")
    print("  3. Panel Member:     panel@demo.vikas (Academic Expert)")
    print("  4. Panel Lead:       panel_lead@demo.vikas (Program Lead)")
    print("  5. Panel Industry:   panel_industry@demo.vikas (Industry Rep)")
    print("  6. District Planner: planner@demo.vikas")
    print("  7. Employer:         employer@demo.vikas")
    print("==================================================")


async def main() -> None:
    async with async_session_maker() as session:
        await seed_demo(session)


if __name__ == "__main__":
    asyncio.run(main())
