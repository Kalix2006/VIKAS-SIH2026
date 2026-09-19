import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { BrowserRouter } from "react-router-dom";
import { ReviewQueue, PanelReviewItem } from "../routes/panel/ReviewQueue";
import * as apiModule from "../lib/api";

vi.mock("../lib/api", () => ({
  api: vi.fn(),
}));

const mockReviews: PanelReviewItem[] = [
  {
    id: "rev-urgent-1",
    skill_gap_id: "gap-1",
    track: "urgent",
    required_signoffs: 2,
    decision: "pending",
    veto_used: false,
    decided_at: null,
    trade_name: "Electrician",
    nsqf_code: "NSQF-L4-ELE",
    district_name: "Pune",
    gap_type: "curriculum_drift",
    gap_score: 72.4,
    nlp_confidence: 0.88,
    job_posting_volume: 85,
    academic_veto_enabled: true,
    votes: [
      {
        id: "vote-1",
        panel_review_id: "rev-urgent-1",
        panel_member_id: "member-1",
        vote: "approve",
        comment: "Drift confirmed against regional solar demand",
        voted_at: "2026-09-19T08:00:00Z",
        panel_role: "industry_professional",
        voter_name: "Industry Rep",
      },
    ],
  },
  {
    id: "rev-standard-1",
    skill_gap_id: "gap-2",
    track: "standard",
    required_signoffs: 4,
    decision: "pending",
    veto_used: false,
    decided_at: null,
    trade_name: "Fitter",
    nsqf_code: "NSQF-L4-FIT",
    district_name: "Nashik",
    gap_type: "oversupply",
    gap_score: 54.0,
    nlp_confidence: 0.91,
    job_posting_volume: 12,
    academic_veto_enabled: true,
    votes: [
      {
        id: "vote-2",
        panel_review_id: "rev-standard-1",
        panel_member_id: "member-2",
        vote: "approve",
        comment: "Agree with oversupply findings",
        voted_at: "2026-09-19T08:30:00Z",
        panel_role: "academic_expert",
        voter_name: "Dr. Sharma",
      },
      {
        id: "vote-3",
        panel_review_id: "rev-standard-1",
        panel_member_id: "member-3",
        vote: "reject",
        comment: "Upcoming factory expansion needs fitters",
        voted_at: "2026-09-19T09:00:00Z",
        panel_role: "industry_professional",
        voter_name: "Mr. Patel",
      },
    ],
  },
];

describe("ReviewQueue Component", () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it("renders urgent and standard track reviews with distinct vote tally formulas", async () => {
    vi.mocked(apiModule.api).mockImplementation(async (path: string) => {
      if (path === "/panel/governance") return { academic_veto_enabled: true };
      if (path === "/panel/queue") return mockReviews;
      throw new Error(`Unhandled path: ${path}`);
    });

    render(
      <BrowserRouter>
        <ReviewQueue />
      </BrowserRouter>
    );

    // Initial load: displays urgent track review by default
    await waitFor(() => {
      expect(screen.getByText("Curriculum Governance Queue")).toBeInTheDocument();
      expect(screen.getByText("Electrician")).toBeInTheDocument();
    });

    // Urgent track displays "1 of 2 needed" tally
    expect(screen.getByText("1 of 2 needed")).toBeInTheDocument();
    expect(screen.getByText("1 approve")).toBeInTheDocument();

    // Verify Academic Veto badge is displayed when enabled
    expect(screen.getByTestId("badge-academic-veto-active")).toBeInTheDocument();
    expect(screen.getAllByText("Academic Veto Active").length).toBeGreaterThan(0);

    // Switch to Standard Track tab
    const standardTab = screen.getByTestId("tab-standard-track");
    fireEvent.click(standardTab);

    // Standard track item displayed
    await waitFor(() => {
      expect(screen.getByText("Fitter")).toBeInTheDocument();
    });

    // Standard track displays "2 of 4 voted" tally
    expect(screen.getByText("2 of 4 voted")).toBeInTheDocument();
    expect(screen.getByText("1 approve")).toBeInTheDocument();
    expect(screen.getByText("1 reject")).toBeInTheDocument();
  });

  it("allows toggling academic veto governance policy", async () => {
    let currentVeto = true;
    vi.mocked(apiModule.api).mockImplementation(async (path: string, options?: any) => {
      if (options?.method === "POST" && path.includes("/panel/governance/toggle")) {
        const body = JSON.parse(options.body);
        currentVeto = body.enabled;
        return { academic_veto_enabled: currentVeto };
      }
      if (path === "/panel/governance") {
        return { academic_veto_enabled: currentVeto };
      }
      if (path === "/panel/queue") {
        return mockReviews;
      }
      throw new Error(`Unhandled path: ${path}`);
    });

    render(
      <BrowserRouter>
        <ReviewQueue />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText("Curriculum Governance Queue")).toBeInTheDocument();
    });

    // Toggle button should show Active initially
    expect(screen.getByText("Active")).toBeInTheDocument();
    const toggleBtn = screen.getByTestId("academic-veto-toggle-btn");
    expect(toggleBtn).toBeInTheDocument();

    fireEvent.click(toggleBtn);

    await waitFor(() => {
      expect(apiModule.api).toHaveBeenCalledWith("/panel/governance/toggle", {
        method: "POST",
        body: JSON.stringify({ enabled: false }),
      });
      // After toggling off, label switches to Standard
      expect(screen.getByText("Standard")).toBeInTheDocument();
    });
  });
});
