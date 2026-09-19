import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { BrowserRouter } from "react-router-dom";
import { DistrictCompare } from "../routes/planner/DistrictCompare";
import * as apiModule from "../lib/api";

vi.mock("../lib/api", () => ({
  api: vi.fn(),
}));

const mockDistricts = {
  districts: [
    { id: "dist-pune", name: "Pune", state: "Maharashtra" },
    { id: "dist-nashik", name: "Nashik", state: "Maharashtra" },
  ],
};

const mockDistrictDetail = {
  trades: [
    { trade_id: "trade-elec", trade_name: "Electrician", nsqf_code: "NSQF-L4-ELE" },
    { trade_id: "trade-fit", trade_name: "Fitter", nsqf_code: "NSQF-L4-FIT" },
  ],
};

const mockCompareResponse = {
  trade_id: "trade-elec",
  trade_name: "Electrician",
  nsqf_code: "NSQF-L4-ELE",
  district_a: {
    district_id: "dist-pune",
    district_name: "Pune",
    state: "Maharashtra",
    alignment_score: 42.0,
    gap_score: 58.0,
    gap_type: "curriculum_drift",
    seats_available: 30,
    job_posting_volume: 120,
    hiring_to_seats_ratio: 4.0,
    top_in_demand_skills: ["Solar PV Maintenance", "PLC Automation", "EV Charging"],
    gap_status: "detected",
  },
  district_b: {
    district_id: "dist-nashik",
    district_name: "Nashik",
    state: "Maharashtra",
    alignment_score: 78.0,
    gap_score: 22.0,
    gap_type: null,
    seats_available: 50,
    job_posting_volume: 45,
    hiring_to_seats_ratio: 0.9,
    top_in_demand_skills: ["Basic Wiring", "Electrical Safety"],
    gap_status: null,
  },
  alignment_score_delta: -36.0,
  comparative_insight:
    "Nashik shows stronger institutional alignment (78.0/100) than Pune (42.0/100). Pune faces notable curriculum divergence against local employers.",
};

describe("DistrictCompare Component", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders comparison selectors, side-by-side cards, alignment delta, and in-demand skills", async () => {
    vi.mocked(apiModule.api).mockImplementation(async (path: string) => {
      if (path === "/planner/map") return mockDistricts;
      if (path.includes("/planner/districts/")) return mockDistrictDetail;
      if (path.includes("/planner/compare")) return mockCompareResponse;
      throw new Error(`Unhandled path: ${path}`);
    });

    render(
      <BrowserRouter>
        <DistrictCompare />
      </BrowserRouter>
    );

    // Initial load
    await waitFor(() => {
      expect(
        screen.getByText("Cross-District Trade Benchmarking")
      ).toBeInTheDocument();
      expect(screen.getByTestId("compare-results")).toBeInTheDocument();
    });

    // Delta banner
    expect(screen.getByText("-36 pts")).toBeInTheDocument();
    expect(
      screen.getByText(/Nashik shows stronger institutional alignment/i)
    ).toBeInTheDocument();

    // District A card
    expect(screen.getByText("Pune")).toBeInTheDocument();
    expect(screen.getByText("42")).toBeInTheDocument();
    expect(screen.getByText("4x")).toBeInTheDocument();
    expect(screen.getByText("Solar PV Maintenance")).toBeInTheDocument();
    expect(screen.getByText("PLC Automation")).toBeInTheDocument();

    // District B card
    expect(screen.getByText("Nashik")).toBeInTheDocument();
    expect(screen.getByText("78")).toBeInTheDocument();
    expect(screen.getByText("0.9x")).toBeInTheDocument();
    expect(screen.getByText("Basic Wiring")).toBeInTheDocument();
  });
});
