"""Development seed script.

Populates initial reference data and test users for local development:
- 2 Districts: Pune, Beed (Maharashtra)
- 5 Locked Trades: Electrician, Fitter, Welder, Automobile/Diesel Mechanic, COPA
- 2 Institutes: Government ITI Pune, Government ITI Beed
- 5 Users: One for each RBAC role (all with password: 'devpass123')
- Associated profile records (PanelMember, TraineeProfile)

Run with:
    python scripts/seed_dev.py
"""

import asyncio
import sys
from pathlib import Path

# Add backend directory to sys.path so app imports work
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.db.session import async_session_maker
from app.models.district import District
from app.models.enums import PanelRoleType, UserRole
from app.models.institute import Institute
from app.models.panel_member import PanelMember
from app.models.trade import Trade
from app.models.trainee_profile import TraineeProfile
from app.models.user import User

DEV_PASSWORD = "devpass123"


async def seed_data(session: AsyncSession) -> None:
    print("Seeding development data...")

    # 1. Districts
    districts_data = [
        {"name": "Pune", "state": "Maharashtra", "lat": 18.5204, "lng": 73.8567},
        {"name": "Beed", "state": "Maharashtra", "lat": 18.9891, "lng": 75.7601},
    ]
    district_map: dict[str, District] = {}
    for d_data in districts_data:
        stmt = select(District).where(District.name == d_data["name"])
        existing = (await session.execute(stmt)).scalar_one_or_none()
        if not existing:
            dist = District(
                name=d_data["name"],
                state=d_data["state"],
                centroid_lat=d_data["lat"],
                centroid_lng=d_data["lng"],
            )
            session.add(dist)
            await session.flush()
            district_map[d_data["name"]] = dist
            print(f"Created district: {dist.name} ({dist.id})")
        else:
            district_map[d_data["name"]] = existing
            print(f"District exists: {existing.name} ({existing.id})")

    # 2. Trades (5 locked starter trades)
    trades_data = [
        {"name": "Electrician", "nsqf_code": "ELE/Q0101"},
        {"name": "Fitter", "nsqf_code": "FIT/Q0101"},
        {"name": "Welder", "nsqf_code": "WLD/Q0101"},
        {"name": "Automobile/Diesel Mechanic", "nsqf_code": "MEC/Q0101"},
        {"name": "COPA", "nsqf_code": "COP/Q0101"},
    ]
    for t_data in trades_data:
        stmt = select(Trade).where(Trade.name == t_data["name"])
        existing_t = (await session.execute(stmt)).scalar_one_or_none()
        if not existing_t:
            trade = Trade(name=t_data["name"], nsqf_code=t_data["nsqf_code"])
            session.add(trade)
            await session.flush()
            print(f"Created trade: {trade.name} ({trade.nsqf_code})")
        else:
            print(f"Trade exists: {existing_t.name}")

    # 3. Institutes
    institutes_data = [
        {"name": "Government ITI Pune", "district": "Pune", "type": "ITI"},
        {"name": "Government ITI Beed", "district": "Beed", "type": "ITI"},
    ]
    institute_map: dict[str, Institute] = {}
    for inst_data in institutes_data:
        stmt = select(Institute).where(Institute.name == inst_data["name"])
        existing_inst = (await session.execute(stmt)).scalar_one_or_none()
        if not existing_inst:
            inst = Institute(
                name=inst_data["name"],
                district_id=district_map[inst_data["district"]].id,
                type=inst_data["type"],
            )
            session.add(inst)
            await session.flush()
            institute_map[inst_data["name"]] = inst
            print(f"Created institute: {inst.name} ({inst.id})")
        else:
            institute_map[inst_data["name"]] = existing_inst
            print(f"Institute exists: {existing_inst.name}")

    # 4. Users (one per role)
    users_data = [
        {
            "email": "trainee@dev.vikas",
            "full_name": "Rohan Shinde (Trainee)",
            "role": UserRole.TRAINEE,
            "district": "Pune",
            "institute": None,
        },
        {
            "email": "institute@dev.vikas",
            "full_name": "Principal ITI Pune (Admin)",
            "role": UserRole.INSTITUTE_ADMIN,
            "district": "Pune",
            "institute": "Government ITI Pune",
        },
        {
            "email": "employer@dev.vikas",
            "full_name": "Tata Motors HR (Employer)",
            "role": UserRole.EMPLOYER,
            "district": "Pune",
            "institute": None,
        },
        {
            "email": "planner@dev.vikas",
            "full_name": "District Skill Officer Pune (Planner)",
            "role": UserRole.PLANNER,
            "district": "Pune",
            "institute": None,
        },
        {
            "email": "panel@dev.vikas",
            "full_name": "Dr. A. K. Verma (Panel Lead)",
            "role": UserRole.PANEL_MEMBER,
            "district": "Pune",
            "institute": None,
            "panel_role": PanelRoleType.PROGRAM_LEAD,
        },
        {
            "email": "panel_expert@dev.vikas",
            "full_name": "Prof. S. N. Joshi (Academic Expert)",
            "role": UserRole.PANEL_MEMBER,
            "district": "Pune",
            "institute": None,
            "panel_role": PanelRoleType.ACADEMIC_EXPERT,
        },
        {
            "email": "panel_industry@dev.vikas",
            "full_name": "Rajesh Nair (Industry Professional)",
            "role": UserRole.PANEL_MEMBER,
            "district": "Pune",
            "institute": None,
            "panel_role": PanelRoleType.INDUSTRY_PROFESSIONAL,
        },
    ]

    for u_data in users_data:
        stmt = select(User).where(User.email == u_data["email"])
        existing_u = (await session.execute(stmt)).scalar_one_or_none()
        if not existing_u:
            inst_id = (
                institute_map[u_data["institute"]].id if u_data["institute"] else None
            )
            user = User(
                email=u_data["email"],
                password_hash=hash_password(DEV_PASSWORD),
                role=u_data["role"],
                full_name=u_data["full_name"],
                district_id=district_map[u_data["district"]].id,
                institute_id=inst_id,
            )
            session.add(user)
            await session.flush()
            print(f"Created user: {user.email} (Role: {user.role.value})")

            # Associated role profiles
            if user.role == UserRole.PANEL_MEMBER:
                pm = PanelMember(
                    user_id=user.id,
                    panel_role=u_data.get("panel_role", PanelRoleType.PROGRAM_LEAD),
                    active=True,
                )
                session.add(pm)
                print(f"Created panel_member profile for: {user.email}")
            elif user.role == UserRole.TRAINEE:
                tp = TraineeProfile(
                    user_id=user.id,
                    district_id=user.district_id,
                    enrolled_course_id=None,
                )
                session.add(tp)
                print(f"Created trainee_profile for: {user.email}")
        else:
            print(f"User exists: {existing_u.email}")

    await session.commit()
    print("\nSeed completed successfully!")


async def main() -> None:
    async with async_session_maker() as session:
        await seed_data(session)


if __name__ == "__main__":
    asyncio.run(main())
