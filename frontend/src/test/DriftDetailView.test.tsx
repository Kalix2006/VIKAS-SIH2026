import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { DriftDetailView } from "../routes/institute/DriftDetailView";
import * as apiModule from "../lib/api";

vi.mock("../lib/api", () => ({
  api: vi.fn(),
}));

vi.mock("recharts", async () => {
  const actual = await vi.importActual<any>("recharts");
  return {
    ...actual,
    ResponsiveContainer: ({ children }: any) => (
      <div data-testid="mock-responsive-container" style={{ width: 500, height: 300 }}>
        {children}
      </div>
    ),
  };
});

const mockDetail = {
  flag_id: "flag-123",
  course_id: "course-123",
  course_name: "Electrician (NSQF-L4)",
  trade_name: "Electrician",
  nsqf_code: "NSQF-L4",
  gap_type: "curriculum_drift",
  gap_score: 64.2,
  reason: "Curriculum drift detected: Local employers require skills not present in standard syllabus.",
  acknowledged: true,
  acknowledged_at: "2026-09-18T12:00:00Z",
  acknowledged_by_name: "Principal Rao",
  score_trend: [
    { timestamp: "Aug 01", gap_score: 30.0, market_demand_factor: 0.6, similarity_score: 0.8 },
    { timestamp: "Aug 15", gap_score: 38.0, market_demand_factor: 0.65, similarity_score: 0.75 },
    { timestamp: "Sep 01", gap_score: 48.0, market_demand_factor: 0.7, similarity_score: 0.7 },
    { timestamp: "Sep 15", gap_score: 64.2, market_demand_factor: 0.75, similarity_score: 0.65 },
  ],
  skills_drifted: [
    "Solar PV Inverter Maintenance",
    "PLC Automation Basics",
    "EV Charging Stations",
  ],
  syllabus_skills: [
    "Electrical Safety Protocols",
    "Wiring Installation",
    "Circuit Breaker Repair",
  ],
  refresher_requested: false,
  refresher_request_id: null,
  score_breakdown: { similarity_score: 0.65, market_demand_factor: 0.75 },
};

describe("DriftDetailView Component", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders trend progression chart container and drifted vs syllabus skills", async () => {
    vi.mocked(apiModule.api).mockResolvedValueOnce(mockDetail);

    render(
      <MemoryRouter initialEntries={["/institute/flags/flag-123/detail"]}>
        <Routes>
          <Route path="/institute/flags/:flagId/detail" element={<DriftDetailView />} />
        </Routes>
      </MemoryRouter>
    );

    // Initial loading finishes
    await waitFor(() => {
      expect(screen.getByText("Curriculum Drift & Trend Analysis")).toBeInTheDocument();
      expect(screen.getByText("Electrician (NSQF-L4) • NSQF Code:")).toBeInTheDocument();
    });

    // Verify Recharts responsive container was rendered
    expect(screen.getByTestId("mock-responsive-container")).toBeInTheDocument();

    // Verify drifted skills list
    expect(screen.getByText("Solar PV Inverter Maintenance")).toBeInTheDocument();
    expect(screen.getByText("PLC Automation Basics")).toBeInTheDocument();
    expect(screen.getByText("EV Charging Stations")).toBeInTheDocument();

    // Verify standard syllabus skills list
    expect(screen.getByText("Electrical Safety Protocols")).toBeInTheDocument();
    expect(screen.getByText("Wiring Installation")).toBeInTheDocument();
  });

  it("opens trainer refresher modal when 'Request Trainer Refresher' button is clicked", async () => {
    vi.mocked(apiModule.api).mockResolvedValueOnce(mockDetail);

    render(
      <MemoryRouter initialEntries={["/institute/flags/flag-123/detail"]}>
        <Routes>
          <Route path="/institute/flags/:flagId/detail" element={<DriftDetailView />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText("Curriculum Drift & Trend Analysis")).toBeInTheDocument();
    });

    const refresherBtn = screen.getByRole("button", { name: /Request Trainer Refresher/i });
    fireEvent.click(refresherBtn);

    // Modal should now be visible in DOM
    expect(
      screen.getByText("Request Trainer Refresher Workshop")
    ).toBeInTheDocument();
    expect(
      screen.getByPlaceholderText(/automated diagnostic tools, PLC wiring/i)
    ).toBeInTheDocument();
  });
});
