import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { ReviewDetailView } from "../routes/panel/ReviewDetailView";
import * as apiModule from "../lib/api";
import * as authModule from "../lib/auth";

vi.mock("../lib/api", () => ({
  api: vi.fn(),
}));

const mockReviewUrgent = {
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
      comment: "Regional industrial demand requires immediate alignment.",
      voted_at: "2026-09-19T08:00:00Z",
      panel_role: "industry_professional",
      voter_name: "Industry Leader",
    },
  ],
};

const mockScoreBreakdown = {
  skill_gap_id: "gap-1",
  gap_score: 72.4,
  nlp_confidence: 0.88,
  gap_type: "curriculum_drift",
  job_posting_volume: 85,
  trade_name: "Electrician",
  district_name: "Pune",
  score_breakdown: {
    similarity_score: 0.62,
    dissimilarity: 0.38,
    volume: 85,
    volume_factor: 0.82,
    volume_weight: 0.6,
    avg_age_days: 14.5,
    recency_decay: 0.9,
    recency_weight: 0.4,
    market_demand_factor: 0.852,
    final_gap_score: 72.4,
    gap_type: "curriculum_drift",
    formula: "Gap Score = (1 - S) × [0.60 × F_v + 0.40 × R]",
  },
};

const mockApprovedReview = {
  ...mockReviewUrgent,
  decision: "approved",
  decided_at: "2026-09-19T10:00:00Z",
  votes: [
    ...mockReviewUrgent.votes,
    {
      id: "vote-2",
      panel_review_id: "rev-urgent-1",
      panel_member_id: "user-panel-expert",
      vote: "approve",
      comment: "Curriculum drift verified against latest state solar initiatives.",
      voted_at: "2026-09-19T10:00:00Z",
      panel_role: "academic_expert",
      voter_name: "Dr. Academic Expert",
    },
  ],
};

describe("ReviewDetailView Component", () => {
  beforeEach(() => {
    vi.resetAllMocks();

    // Default mock user: Academic Expert
    vi.spyOn(authModule, "useAuth").mockReturnValue({
      user: {
        id: "user-panel-expert",
        email: "panel_expert@dev.vikas",
        full_name: "Dr. Academic Expert",
        role: "panel_member",
        district_id: "dist-1",
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

  it("renders non-black-box score breakdown with formula, components, and weights", async () => {
    vi.mocked(apiModule.api).mockImplementation(async (path: string) => {
      if (path.includes("score-breakdown")) return mockScoreBreakdown;
      if (path.includes("/panel/reviews/")) return mockReviewUrgent;
      throw new Error(`Unhandled path: ${path}`);
    });

    render(
      <MemoryRouter initialEntries={["/panel/reviews/rev-urgent-1"]}>
        <Routes>
          <Route path="/panel/reviews/:reviewId" element={<ReviewDetailView />} />
        </Routes>
      </MemoryRouter>
    );

    // Header and trade info
    await waitFor(() => {
      expect(screen.getByText("Auditable Algorithmic Breakdown")).toBeInTheDocument();
      expect(screen.getByText("Electrician")).toBeInTheDocument();
      expect(screen.getByText("Pune")).toBeInTheDocument();
    });

    // Mathematical formula banner
    expect(
      screen.getByText("Final Gap Score = 100 × (1 - S) × [0.60 × F_V + 0.40 × R]")
    ).toBeInTheDocument();

    // Components and weights
    expect(screen.getByText("1. Curriculum Divergence")).toBeInTheDocument();
    expect(screen.getByText("Complement (1 - S)")).toBeInTheDocument();
    expect(screen.getByText("2. Vacancy Volume (F_V)")).toBeInTheDocument();
    expect(screen.getByText("3. Recency Decay (R)")).toBeInTheDocument();
    expect(screen.getByText("Weight: 60%")).toBeInTheDocument();
    expect(screen.getByText("Weight: 40%")).toBeInTheDocument();

    // Audit trail of existing votes
    expect(screen.getByText("industry professional")).toBeInTheDocument();
    expect(screen.getByText("Industry Leader")).toBeInTheDocument();
    expect(
      screen.getByText(/Regional industrial demand requires immediate alignment/i)
    ).toBeInTheDocument();
  });

  it("submits vote and immediately transitions review status to APPROVED without page reload", async () => {
    vi.mocked(apiModule.api).mockImplementation(async (path: string, options?: any) => {
      if (options?.method === "POST" && path.includes("/vote")) {
        return mockApprovedReview;
      }
      if (path.includes("score-breakdown")) return mockScoreBreakdown;
      if (path.includes("/panel/reviews/")) return mockReviewUrgent;
      throw new Error(`Unhandled path: ${path}`);
    });

    render(
      <MemoryRouter initialEntries={["/panel/reviews/rev-urgent-1"]}>
        <Routes>
          <Route path="/panel/reviews/:reviewId" element={<ReviewDetailView />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText("Panel Member Voting Station")).toBeInTheDocument();
    });

    // Enter comment
    const commentInput = screen.getByPlaceholderText(
      /Reviewed lab tooling requirements/i
    );
    fireEvent.change(commentInput, {
      target: { value: "Curriculum drift verified against latest state solar initiatives." },
    });

    // Click submit vote
    const submitBtn = screen.getByRole("button", { name: /Cast Official Vote/i });
    fireEvent.click(submitBtn);

    // Check API was called
    await waitFor(() => {
      expect(apiModule.api).toHaveBeenCalledWith(
        "/panel/reviews/rev-urgent-1/vote",
        {
          method: "POST",
          body: JSON.stringify({
            vote: "approve",
            comment: "Curriculum drift verified against latest state solar initiatives.",
          }),
        }
      );
    });

    // Verify live update: banner announces approval and status pill says APPROVED
    await waitFor(() => {
      expect(
        screen.getByText("Vote recorded! Signoff requirement satisfied — Proposal is now APPROVED.")
      ).toBeInTheDocument();
      expect(screen.getByTestId("badge-review-decision")).toHaveTextContent("approved");
    });
  });

  it("displays academic veto warning badge on reject option for academic expert", async () => {
    vi.mocked(apiModule.api).mockImplementation(async (path: string) => {
      if (path.includes("score-breakdown")) return mockScoreBreakdown;
      if (path.includes("/panel/reviews/")) return mockReviewUrgent;
      throw new Error(`Unhandled path: ${path}`);
    });

    render(
      <MemoryRouter initialEntries={["/panel/reviews/rev-urgent-1"]}>
        <Routes>
          <Route path="/panel/reviews/:reviewId" element={<ReviewDetailView />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText("Panel Member Voting Station")).toBeInTheDocument();
    });

    // Check that Reject option displays (VETO) warning for academic expert
    expect(screen.getByText(/Reject \(VETO\)/i)).toBeInTheDocument();
    expect(
      screen.getByText(/Exercises statutory Academic Veto: will immediately reject the proposal/i)
    ).toBeInTheDocument();

    // Select reject radio
    const rejectRadio = screen.getByDisplayValue("reject");
    fireEvent.click(rejectRadio);
    expect(rejectRadio).toBeChecked();
  });
});
