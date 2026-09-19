import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import {
  AlternativesView,
  AlternativesGuide,
} from "../routes/trainee/AlternativesView";
import * as apiModule from "../lib/api";

vi.mock("../lib/api", () => ({
  api: vi.fn(),
}));

const mockGuide: AlternativesGuide = {
  flagged_course_name: "Fitter",
  flagged_institute_name: "Government ITI Pune",
  guidance_message:
    "Career Guidance Note: While the Fitter curriculum provides valuable foundational knowledge, local industries in your district are currently seeking updated modern competencies.",
  alternatives: [
    {
      id: "alt-1",
      institute_id: "inst-1",
      institute_name: "Government ITI Pune",
      trade_id: "trade-1",
      trade_name: "Electrician",
      nsqf_code: "ELE/Q0101",
      seats_available: 24,
      status: "active",
      demand_label: "Strong local demand",
      recommendation_rationale:
        "Accredited active program with 24 open seats and strong hiring alignment.",
    },
  ],
};

describe("AlternativesView Component", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders empathetic guidance banner without raw metrics", async () => {
    vi.mocked(apiModule.api).mockResolvedValueOnce(mockGuide);
    const onBack = vi.fn();

    render(<AlternativesView courseId="course-2" onBack={onBack} />);

    await waitFor(() => {
      expect(
        screen.getByText("Career Alignment Guidance")
      ).toBeInTheDocument();
    });

    // Check empathetic guidance message
    expect(
      screen.getByText(/Career Guidance Note: While the Fitter curriculum/i)
    ).toBeInTheDocument();

    // Verify recommended alternative is displayed
    expect(screen.getByText("Electrician")).toBeInTheDocument();
    expect(screen.getByText("Strong local demand")).toBeInTheDocument();
    expect(
      screen.getByText(/Accredited active program with 24 open seats/i)
    ).toBeInTheDocument();

    // Verify back navigation
    const backBtn = screen.getByText("Back to Course Catalog");
    fireEvent.click(backBtn);
    expect(onBack).toHaveBeenCalledTimes(1);
  });
});

