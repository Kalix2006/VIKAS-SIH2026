import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { BrowserRouter } from "react-router-dom";
import { AggregateReadinessView } from "../routes/employer/AggregateReadinessView";
import * as apiModule from "../lib/api";
import * as authModule from "../lib/auth";

vi.mock("../lib/api", () => ({
  api: vi.fn(),
}));

const mockReadinessData = {
  trade_id: "trade-elec",
  trade_name: "Electrician",
  nsqf_code: "NSQF-L4-ELE",
  district_id: "dist-pune",
  district_name: "Pune",
  total_enrolled_trainees: 140,
  graduating_within_90_days: 58,
  cohort_readiness_index: 79.4,
  readiness_distribution: {
    high_readiness: 67,
    moderate_readiness: 53,
    foundational: 20,
  },
  competency_mastery: [
    {
      competency_name: "Multimeter & Megger Diagnostics",
      category: "Core Tool",
      mastery_percentage: 91.5,
    },
    {
      competency_name: "Industrial Control Panel Assembly",
      category: "Technical Competency",
      mastery_percentage: 82.0,
    },
    {
      competency_name: "Solar Rooftop On-Grid Inverter Wiring",
      category: "Emerging Industry Tech",
      mastery_percentage: 64.0,
    },
  ],
  contributing_institutes_count: 3,
  privacy_guarantee:
    "Aggregate readiness metrics strictly anonymized per VIKAS Data Protection & Privacy-by-Design Guidelines. Zero candidate PII or individual trainee identifiers exposed.",
};

describe("AggregateReadinessView Component", () => {
  beforeEach(() => {
    vi.resetAllMocks();

    vi.spyOn(authModule, "useAuth").mockReturnValue({
      user: {
        id: "emp-user-1",
        email: "employer@dev.vikas",
        full_name: "Tata Motors Plant HR",
        role: "employer",
        district_id: "dist-pune",
        institute_id: null,
      },
      login: vi.fn(),
      logout: vi.fn(),
      quickLoginAsTrainee: vi.fn(),
      quickLoginAsInstituteAdmin: vi.fn(),
      quickLoginAsPanelMember: vi.fn(),
      quickLoginAsPlanner: vi.fn(),
      quickLoginAsEmployer: vi.fn(),
      loading: false,
    });
  });

  it("renders statistical aggregate readiness and passes strict privacy audit (zero candidate PII)", async () => {
    vi.mocked(apiModule.api).mockImplementation(async (path: string) => {
      if (path.includes("/employer/aggregate-readiness")) {
        return mockReadinessData;
      }
      if (path.includes("/trainee/courses")) {
        return [
          { trade_id: "trade-elec", trade_name: "Electrician", nsqf_code: "NSQF-L4-ELE" },
        ];
      }
      throw new Error(`Unhandled path: ${path}`);
    });

    const { container } = render(
      <BrowserRouter>
        <AggregateReadinessView />
      </BrowserRouter>
    );

    // Verify statutory privacy banner and statistical data
    await waitFor(() => {
      expect(screen.getByTestId("privacy-banner")).toBeInTheDocument();
      expect(
        screen.getByText("Privacy-by-Design Governance Guarantee")
      ).toBeInTheDocument();
      expect(screen.getByTestId("stat-enrolled")).toHaveTextContent("140");
    });

    // Verify remaining statistical KPI cards
    expect(screen.getByTestId("stat-graduating")).toHaveTextContent("58");
    expect(screen.getByTestId("stat-readiness-index")).toHaveTextContent("79.4%");

    // Verify distribution tiers
    expect(screen.getByText("High Readiness")).toBeInTheDocument();
    expect(screen.getByText("Moderate Readiness")).toBeInTheDocument();
    expect(screen.getByText("Foundational")).toBeInTheDocument();

    // Verify competency bars
    expect(screen.getByText("Multimeter & Megger Diagnostics")).toBeInTheDocument();
    expect(screen.getByText("91.5%")).toBeInTheDocument();

    // =========================================================================
    // STRICT PRIVACY AUDIT ASSERTION:
    // Verify that NO individual candidate/trainee identifiable data exists in
    // the rendered DOM (HTML or text content).
    // =========================================================================
    const renderedHtml = container.innerHTML.toLowerCase();
    const renderedText = container.textContent?.toLowerCase() || "";

    const FORBIDDEN_IDENTIFIERS = [
      "trainee_id",
      "candidate_id",
      "student_id",
      "roll_number",
      "candidate name",
      "trainee name",
      "student name",
      "phone number",
      "mobile number",
      "aadhaar",
      "date of birth",
      "rohan shinde", // Sample seed trainee name
      "trainee@vikas",
      "trainee@dev.vikas",
    ];

    FORBIDDEN_IDENTIFIERS.forEach((identifier) => {
      expect(renderedHtml).not.toContain(identifier);
      expect(renderedText).not.toContain(identifier);
    });
  });
});
