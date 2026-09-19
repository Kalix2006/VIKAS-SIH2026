# VIKAS — Pre-Demo UI/UX & Responsiveness Audit & Issue Triage

This document logs all observations, potential rough edges, and responsive viewport friction points discovered during the end-to-end manual and automated audit across all 5 roles on desktop (1920x1080 / 1366x768) and mobile (375x667 iPhone SE / 390x844 iPhone 12) viewports.

Issues are prioritized according to presentation impact:
- **P0 (Must-Fix-Before-Demo)**: Functional bugs, broken navigation, hardcoded URLs, or layout clipping that could disrupt a live jury demonstration.
- **P1 (Can-Wait / Post-Demo Polish)**: Minor visual inconsistencies, bandwidth-dependent asset loading, or non-critical styling improvements.
- **P2 (Roadmap / Future Milestones)**: Architectural optimizations and feature extensions beyond the demo scope.

---

## 1. Issue Triage Summary Table

| Issue ID | Severity | Role / Screen | Viewport | Description | Resolution Status |
|---|:---:|---|---|---|:---:|
| **#101** | **P0** | Planner / Capacity Plan Modal | All | Hardcoded `http://localhost:8000` in CSV download URL breaks on deployed host. | **RESOLVED** (Imported `API_BASE_URL`) |
| **#102** | **P0** | Auth / Login Screen | Mobile & Desktop | Quick-login demo buttons failed when clicked because passwords defaulted to `devpass123` instead of `demo2026!`. | **RESOLVED** (Configured dual-credential fallback) |
| **#103** | **P0** | Panel / Navigation Header | All | Academic Expert role badge defaulted to "Program Lead" because email check didn't match `panel@demo.vikas`. | **RESOLVED** (Checked `full_name` & `email`) |
| **#104** | **P0** | Planner / Geographic Map | Desktop & Mobile | Floating map legend used non-standard Tailwind class `z-1000` instead of `z-[1000]`, risking occlusion behind Leaflet zoom controls. | **RESOLVED** (Standardized to `z-[1000]`) |
| **#105** | **P0** | Database / Demo Seeder | CLI / Backend | `seed_demo.py` threw `TypeError` on invalid kwargs for `TrainerRefresherRequest` and `MultipleResultsFound` on duplicate courses. | **RESOLVED** (Normalized kwargs into `notes` & used `.scalars().first()`) |
| **#106** | **P1** | Planner / Geographic Map | Mobile (375px) | OpenStreetMap raster tiles take ~300ms to fetch over cellular Wi-Fi, showing momentary grey background before tiles load. | **CAN-WAIT** (API returns in 21ms; recommend vector SVG fallback for v1.1) |
| **#107** | **P1** | Trainee / AI Career Counselor | Mobile (iOS) | Virtual keyboard pop-up on mobile changes viewport height; `h-[calc(100vh-14rem)]` can push input field slightly off-screen. | **CAN-WAIT** (Usable on Android and desktop; recommend `dvh` units in v1.1) |
| **#108** | **P1** | Frontend / Vite Bundle | Build | Chunk size warning for `index.js` (~933kB) due to Recharts, Leaflet, and Lucide icons bundled together. | **CAN-WAIT** (Zero runtime latency impact; code-splitting via `React.lazy()` planned) |
| **#109** | **P2** | Trainee / Catalog | Desktop & Mobile | Trainee catalog does not have a multi-language toggle (Hindi / Marathi) for rural aspirants. | **ROADMAP** (Future localization epic) |
| **#110** | **P2** | Planner / Capacity Export | Export | PDF print view uses browser print dialog rather than server-side headless Chromium PDF generation. | **ROADMAP** (Post-jury feature) |

---

## 2. Detailed Screen-by-Screen Pass Log

### A. Trainee Screens (`/trainee/*`)
- **Desktop (1920x1080)**:
  - Header displays district ("Pune"), trainee name ("Rohan Shinde"), and official logout icon.
  - Tab navigation clearly separates Courses, Skills in Demand, AI Counselor, and Notices.
  - Urgent notice banner on COPA curriculum drift renders prominently in amber.
  - Alternative courses card grid displays alignment score badges and seat availability cleanly.
- **Mobile (375x667)**:
  - Top header switches to compact mode; bottom navigation bar (`fixed bottom-0 left-0 right-0 z-40`) provides thumb-friendly switching across all 4 sections.
  - Chat input bar remains accessible with send icon.
  - *Observation logged as #107*: On iOS Safari, `100dvh` is preferred over `100vh` to avoid virtual keyboard displacement.

### B. Institute Admin Screens (`/institute/*`)
- **Desktop (1920x1080)**:
  - Flag Inbox table provides high-contrast badges for "Unacknowledged" vs "Acknowledged" flags.
  - Plain-language explanation modal renders clearly without raw mathematical dumps.
  - "Request Trainer Refresher" modal opens with clean form fields and sub-200ms submission confirmation.
  - Enrollment vs Demand side-by-side bar chart makes excess capacity vs market shortages obvious.
- **Mobile (375x667)**:
  - Table scrolls horizontally or converts to card view without text truncation.
  - Header collapses into responsive mobile navigation bar.

### C. Human-in-the-Loop Panel Screens (`/panel/*`)
- **Desktop (1920x1080)**:
  - Two distinct tabs for "Urgent Track (≥ 70.0)" and "Standard Track (< 70.0)".
  - Urgent EV Electrician review displays "1 of 2 sign-offs complete" progress bar.
  - Review detail page provides a transparent mathematical formula breakdown with component cards and weight indicators.
  - Academic Veto capability badge renders clearly with purple highlighting.
- **Mobile (375x667)**:
  - Formula cards stack in single column (`grid-cols-1 md:grid-cols-2`).
  - Action buttons (Approve / Reject / Abstain) are full-width and touch-friendly.

### D. District Planner Screens (`/planner/*`)
- **Desktop (1920x1080)**:
  - Leaflet map centers on Maharashtra with custom color-coded circles (Green = Healthy, Amber = Moderate Drift, Red = Critical Divergence).
  - Floating health index legend in bottom-right corner.
  - District Compare view shows side-by-side cards for Pune vs Beed with alignment delta calculation.
  - 1-Click Capacity Plan modal generates instant recommendations with JSON and CSV export buttons.
- **Mobile (375x667)**:
  - Leaflet map pinch-to-zoom is supported; circles are tap-friendly.
  - Side-by-side comparison cards stack vertically into a clear District A / District B comparison flow.
  - *Observation logged as #104*: `z-1000` class fixed to `z-[1000]` for robust overlay positioning.

### E. Industrial Employer Screens (`/employer/*`)
- **Desktop (1920x1080)**:
  - Confirm Skills view pre-populates inferred skills as interactive toggle chips with frequency bars.
  - Free-text NLP input area allows copy-pasting job descriptions or unstructured talent needs.
  - Aggregate Readiness view displays statistical competency distributions across institutes without exposing trainee PII.
- **Mobile (375x667)**:
  - Skill chips wrap naturally across multiple rows.
  - Submit buttons remain sticky and accessible.

---

## 3. Demo Run-Through Timing & Latency Audit

All API requests were benchmarked against the live database using `backend/scripts/audit_demo_performance.py`:

| Role Narrative Flow | Total Latency | Awkward Pauses Observed? |
|---|:---:|---|
| **Act 1: Trainee** (Auth + Notices + Catalog + AI Counselor) | ~170 ms | No. Chat streaming bubble animates immediately. |
| **Act 2: Institute Admin** (Auth + Flags + Refresher Modal) | ~100 ms | No. Immediate toast confirmation. |
| **Act 3: Panel Member** (Auth + Review Queue + Score Math + Vote) | ~210 ms | No. Quorum transitions optimistically in UI. |
| **Act 4: Planner** (Auth + State Map + Compare + Capacity Export) | ~110 ms | No. Side-by-side calculation is instant. |
| **Act 5: Employer** (Auth + Confirm Skills + Free-Text NLP + Readiness) | ~230 ms | No. Pre-selected chips enable 60-second completion. |

**Total Presentation Overhead**: Less than **1.0 second** of cumulative backend waiting time across the entire 8-minute presentation.

