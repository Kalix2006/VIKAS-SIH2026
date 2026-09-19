import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { BrowserRouter } from "react-router-dom";
import { DistrictMap, PlannerMapResponse } from "../routes/planner/DistrictMap";
import * as apiModule from "../lib/api";

// Mock react-leaflet for JSDOM test environment
vi.mock("react-leaflet", () => ({
  MapContainer: ({ children }: any) => <div data-testid="mock-map-container">{children}</div>,
  TileLayer: () => <div data-testid="mock-tile-layer" />,
  CircleMarker: ({ children, center }: any) => (
    <div data-testid={`mock-circle-marker-${center[0]}-${center[1]}`}>{children}</div>
  ),
  Popup: ({ children }: any) => <div data-testid="mock-popup">{children}</div>,
}));

vi.mock("../lib/api", () => ({
  api: vi.fn(),
}));

const mockMapResponse: PlannerMapResponse = {
  districts: [
    {
      id: "dist-1",
      name: "Pune",
      state: "Maharashtra",
      centroid_lat: 18.5204,
      centroid_lng: 73.8567,
      active_trades_count: 5,
      flagged_trades_count: 2,
      total_job_volume: 380,
      alignment_health_score: 42.5,
      health_category: "Critical Divergence",
      divergence_index: 57.5,
    },
    {
      id: "dist-2",
      name: "Nashik",
      state: "Maharashtra",
      centroid_lat: 19.9975,
      centroid_lng: 73.7898,
      active_trades_count: 4,
      flagged_trades_count: 0,
      total_job_volume: 120,
      alignment_health_score: 82.0,
      health_category: "Healthy",
      divergence_index: 18.0,
    },
  ],
  state_avg_health: 62.3,
  total_districts: 2,
  critical_districts_count: 1,
  formula_definition:
    "Alignment Health Index (AHI) = 100 - [Sum(Gap_Score * ln(1 + Volume)) / Sum(ln(1 + Volume))]",
};

describe("DistrictMap Component", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders state KPI summary cards and empirical AHI formula banner", async () => {
    vi.mocked(apiModule.api).mockResolvedValueOnce(mockMapResponse);

    render(
      <BrowserRouter>
        <DistrictMap />
      </BrowserRouter>
    );

    // Header & KPIs
    await waitFor(() => {
      expect(screen.getByText("State Skill Alignment Heatmap")).toBeInTheDocument();
      expect(screen.getByTestId("kpi-total-districts")).toHaveTextContent("2");
      expect(screen.getByTestId("kpi-state-avg-health")).toHaveTextContent("62.3");
      expect(screen.getByTestId("kpi-critical-districts")).toHaveTextContent("1");
    });

    // Formula definition
    expect(
      screen.getByText(/AHI = 100 - \[∑\(Gap_Score × ln\(1 \+ Volume\)\) \/ ∑\(ln\(1 \+ Volume\)\)\]/i)
    ).toBeInTheDocument();

    // Map container & Leaflet markers rendered
    expect(screen.getByTestId("mock-map-container")).toBeInTheDocument();
    expect(
      screen.getByTestId("mock-circle-marker-18.5204-73.8567")
    ).toBeInTheDocument();
    expect(
      screen.getByTestId("mock-circle-marker-19.9975-73.7898")
    ).toBeInTheDocument();

    // Popup contents rendered in DOM
    expect(screen.getByText("Pune")).toBeInTheDocument();
    expect(screen.getByText("Nashik")).toBeInTheDocument();
    expect(screen.getByText("42.5/100")).toBeInTheDocument();
    expect(screen.getByText("82/100")).toBeInTheDocument();

    // Drill down links available
    const drillDownLinks = screen.getAllByRole("link", { name: /Drill Down Table/i });
    expect(drillDownLinks).toHaveLength(2);
    expect(drillDownLinks[0]).toHaveAttribute("href", "/planner/districts/dist-1");
  });
});

