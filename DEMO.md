# VIKAS — Jury Presentation & Live Demo Playbook

> **Platform**: Viksit India Kaushal Alignment System (VIKAS)  
> **Demo Duration**: 6 – 8 Minutes  
> **Audience**: Hackathon Jury / Skilling Ecosystem Stakeholders  

---

## 1. Quick Start & Environment Verification

### Prerequisites
Make sure PostgreSQL is running, the backend is up on port 8000, and the frontend Vite dev server is on port 5173.

```bash
# 1. Populate/Reset the Realistic Demo Dataset (Idempotent)
cd backend
.venv\Scripts\python.exe scripts/seed_demo.py

# 2. Start Backend (if not already running)
.venv\Scripts\uvicorn app.main:app --reload --port 8000

# 3. Start Frontend (in separate terminal)
cd ../frontend
npm run dev
```

Visit: `http://localhost:5173`

---

## 2. Demo User Credentials Reference

Every role has a pre-configured account with the universal demo password: **`demo2026!`**

| Role | Email | Name / Organization | Primary Demo Screen |
|---|---|---|---|
| **Trainee** | `trainee@demo.vikas` | Rohan Shinde (ITI Student) | `/trainee/alerts`, `/trainee/chat` |
| **Institute Admin** | `institute@demo.vikas` | Dr. V. M. Kulkarni (Principal, ITI Pune) | `/institute/flags`, `/institute/enrollment-vs-demand` |
| **Panel Member** | `panel@demo.vikas` | Prof. S. N. Joshi (Academic Expert) | `/panel/queue`, `/panel/reviews/:id` |
| **District Planner** | `planner@demo.vikas` | Dr. Sunita Deshmukh (District Skill Officer) | `/planner/map`, `/planner/compare` |
| **Employer** | `employer@demo.vikas` | Anand Mahindra (Tata Motors Talent Lead) | `/employer/validate`, `/employer/aggregate-readiness` |

*Additional Panel Accounts for multi-voter quorum demos:*
- Program Lead: `panel_lead@demo.vikas`
- Industry Rep: `panel_industry@demo.vikas`

---

## 3. The 5-Act Narrative Walkthrough Script

### Act 1: The Trainee — "Closing the Information Asymmetry"
*Persona: Rohan Shinde, enrolled in COPA (Computer Operator & Programming Assistant) at Govt ITI Pune.*

1. **Login**: Sign in as `trainee@demo.vikas` / `demo2026!`.
2. **The Hook (What Rohan Sees)**:
   - Rohan lands directly on his personal dashboard. He sees his enrolled course: **COPA (Pune)**.
   - **Market Drift Alert Banner**: Point out the highlighted advisory:
     > *"Market Advisory for COPA: Local IT firms in Pune report a 40% surge in demand for Python and SQL automation. Consider taking the approved weekend Python Bridging module."*
   - Explain to the jury: *“Traditional vocational students discover curriculum obsolescence on interview day. In VIKAS, trainees get pro-active market intelligence while they are still in the classroom.”*
3. **Action — Alternative / Bridge Courses**:
   - Click **"Explore Alternatives"**: Rohan sees matched bridging modules with alignment scores and available seats.
4. **Action — AI Career Guidance**:
   - Navigate to **"AI Career Counselor"** (`/trainee/chat`).
   - Type or click suggestion: *"What skills do Pune employers look for in COPA graduates?"*
   - Observe fast streaming response synthesized from live district job data with deterministic fallback safeguard.

---

### Act 2: The Institute Admin — "From Blind Syllabus to Responsive Skilling"
*Persona: Dr. V. M. Kulkarni, Principal of Government ITI Pune (Aundh).*

1. **Login**: Sign in as `institute@demo.vikas` / `demo2026!`.
2. **The Hook (Curriculum Drift Flags)**:
   - Lands on **Flag Inbox** (`/institute/flags`).
   - Principal sees 2 flagged trades:
     1. **Automobile/Diesel Mechanic**: Flagged for *Electronic Fuel Injection & OBD-II Diagnostics*.
     2. **COPA**: Flagged for *Python Scripting & Cloud Data*.
   - Emphasize to jury: *“The principal does not see confusing raw vector math or cosine similarities. VIKAS translates data science into actionable plain language reasons.”*
3. **Action — Acknowledge & Request Upskilling**:
   - Click on the Automobile Mechanic flag detail.
   - Show the **"Request Trainer Refresher"** button. Point out the already logged request:
     > *"Our mechanical workshop requires immediate training for 4 trainers on OBD-II diagnostic scanners."*
   - Explain: *“Instead of blaming instructors for outdated curricula, VIKAS closes the loop by connecting flagged courses to state-funded faculty upskilling.”*
4. **Action — Enrollment vs Market Demand**:
   - Switch to **"Enrollment vs Demand"** view.
   - Highlight the gap: Electrician has 148 market postings vs 120 seats, while traditional trades are oversaturated.

---

### Act 3: The Panel Member — "Human-in-the-Loop Governance"
*Persona: Prof. S. N. Joshi, Academic Expert on the Maharashtra Vocational Governance Board.*

1. **Login**: Sign in as `panel@demo.vikas` / `demo2026!`.
2. **The Hook (Dual-Track Review Queue)**:
   - Lands on **Review Queue** (`/panel/queue`).
   - Show the two distinct urgency tracks:
     - **Urgent Track**: Electrician (Pune) — *EV Powertrain & BMS Diagnostics* (1 of 2 sign-offs complete).
     - **Standard Track**: Welder (Beed) — *Robotic / TIG Welding* (0 of 2 sign-offs complete).
3. **Action — Non-Black-Box Score Inspection**:
   - Click **Review** on the Urgent EV Electrician gap.
   - Show the transparent mathematical breakdown:
     $$\text{Gap Score (78.5)} = 0.35 \times \text{Volume} + 0.30 \times \text{Velocity} + 0.20 \times \text{Cosine Distance} + 0.15 \times \text{Employer Validation}$$
   - Point out the **Academic Veto Badge**: Explain that academic experts have statutory veto power to prevent fly-by-night fads from corrupting formal qualifications.
4. **Action — Cast Decisive Vote**:
   - Add comment: *"Approved for immediate 40-hour EV safety lab addition."*
   - Click **Approve**. The review reaches quorum, transitions to `approved`, and dispatches institutional alerts automatically.

---

### Act 4: The District Skill Planner — "Macro-Resource Allocation"
*Persona: Dr. Sunita Deshmukh, District Skill Development Officer.*

1. **Login**: Sign in as `planner@demo.vikas` / `demo2026!`.
2. **The Hook (District Alignment Health Map)**:
   - Lands on **Maharashtra Heat Map** (`/planner/map`).
   - Observe aggregate district health indicators:
     - **Pune**: High demand volume, rapid EV transition velocity.
     - **Beed**: Agro-industrial focus, high demand for heavy welding and agricultural equipment repair.
3. **Action — Side-by-Side District Compare**:
   - Navigate to **"Compare Districts"** (`/planner/compare`).
   - Select **District A = Pune**, **District B = Beed**, **Trade = Welder**.
   - Show the side-by-side card comparison:
     - Pune Welder: Demands 6G TIG argon shielding and aerospace stainless-steel fabrication.
     - Beed Welder: Demands heavy tractor trailer and sugarcane harvester arc welding.
   - Explain: *“A national syllabus cannot treat Pune and Beed identically. VIKAS enables hyper-local vocational tailoring.”*
4. **Action — 1-Click Capacity Plan Export**:
   - Click **"Export Capacity Plan"** for Pune.
   - Instantly generate and download structured recommendations for seat re-allocation, trainer deployment, and lab equipment grants.

---

### Act 5: The Employer — "Industry Co-Creation in Under 60 Seconds"
*Persona: Anand Mahindra, Talent Acquisition Lead at Tata Motors.*

1. **Login**: Sign in as `employer@demo.vikas` / `demo2026!`.
2. **The Hook (60-Second Skill Confirmation)**:
   - Lands on **Confirm Skills** (`/employer/validate`).
   - Select **Trade = Electrician**, **District = Pune**.
   - Show the pre-filled inferred skills as interactive chips: *EV Battery Assembly, High Voltage Safety, CAN Bus*.
   - Click to adjust urgency weights.
3. **Action — Unstructured Natural Language Input**:
   - In the text box, paste or type:
     > *"Need 30 technicians with strong high-voltage DC safety protocols and thermal cooling loop assembly for our Chakan facility."*
   - Click **Submit Validation**. System extracts the skill signatures while maintaining complete data lineage.
4. **Action — Privacy-by-Design Talent Readiness**:
   - Navigate to **"Aggregate Readiness"** (`/employer/aggregate-readiness`).
   - Employer sees aggregate readiness distributions across Pune ITIs without any individual candidate PII (privacy-by-design compliance).

---

## 4. Emergency & Offline Resilience Cheat Sheet

| Potential Live Demo Glitch | Built-In Fail-Safe / Workaround |
|---|---|
| **Groq API latency or rate-limiting** | The system automatically falls back to pre-compiled high-fidelity deterministic templates. No crash or blank screen. |
| **Leaflet Map tiles slow on conference Wi-Fi** | Map markers and district polygons render with fallback SVG vector coordinates. |
| **Accidental database modification** | Run `.venv\Scripts\python.exe scripts/seed_demo.py` in 3 seconds to restore pristine demo state. |
| **Token expiration during demo** | Demo tokens default to generous lifespans with seamless refresh. If logged out, use quick credentials in Section 2. |

---

## 5. Timing Budget Breakdown

```
0:00 - 0:45 | Introduction & Problem: 1.5M vocational students vs rigid national syllabi
0:45 - 2:00 | Act 1: The Trainee (Alerts, Alternatives, Career Chat)
2:00 - 3:15 | Act 2: The Institute Admin (Flag Inbox, Refresher Request)
3:15 - 4:45 | Act 3: The Panel Member (Urgent Quorum, Transparent Math Formula, Veto)
4:45 - 6:00 | Act 4: The District Planner (Maharashtra Map, Pune vs Beed Compare, Export)
6:00 - 7:00 | Act 5: The Employer (60s Validation, Unstructured Ingestion, Privacy Readiness)
7:00 - 8:00 | Wrap-up, Architecture Summary & Q&A
```

