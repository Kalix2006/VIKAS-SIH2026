import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { BrowserRouter } from "react-router-dom";
import { FlagInbox, InstituteFlag } from "../routes/institute/FlagInbox";
import * as apiModule from "../lib/api";

vi.mock("../lib/api", () => ({
  api: vi.fn(),
}));

const mockFlags: InstituteFlag[] = [
  {
    flag_id: "flag-1",
    course_id: "course-1",
    course_name: "Fitter (NSQF-L4-FIT)",
    trade_name: "Fitter",
    nsqf_code: "NSQF-L4-FIT",
    seats_available: 30,
    course_status: "flagged",
    gap_type: "curriculum_drift",
    gap_score: 62.5,
    job_posting_volume: 45,
    reason: "Curriculum drift detected: Local employers require skills not present in standard syllabus.",
    acknowledged: false,
    acknowledged_at: null,
    acknowledged_by_name: null,
    created_at: "2026-09-18T10:00:00Z",
  },
  {
    flag_id: "flag-2",
    course_id: "course-2",
    course_name: "Welder (NSQF-L3-WLD)",
    trade_name: "Welder",
    nsqf_code: "NSQF-L3-WLD",
    seats_available: 20,
    course_status: "flagged",
    gap_type: "oversupply",
    gap_score: 55.0,
    job_posting_volume: 5,
    reason: "Oversupply detected: High training output relative to local hiring volume.",
    acknowledged: true,
    acknowledged_at: "2026-09-18T11:30:00Z",
    acknowledged_by_name: "Principal Rao",
    created_at: "2026-09-18T09:00:00Z",
  },
];

describe("FlagInbox Component", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders flag list with visual distinction for unacknowledged flags and plain reasons", async () => {
    vi.mocked(apiModule.api).mockResolvedValueOnce(mockFlags);

    render(
      <BrowserRouter>
        <FlagInbox />
      </BrowserRouter>
    );

    // Shows loading then loaded items
    await waitFor(() => {
      expect(screen.getByText("Fitter (NSQF-L4-FIT)")).toBeInTheDocument();
      expect(screen.getByText("Welder (NSQF-L3-WLD)")).toBeInTheDocument();
    });

    // Plain-language reasons
    expect(
      screen.getByText(/Curriculum drift detected/i)
    ).toBeInTheDocument();
    expect(screen.getByText(/Oversupply detected/i)).toBeInTheDocument();

    // Visual indicators: flag-1 has an Acknowledge button, flag-2 shows Reviewed
    expect(screen.getByRole("button", { name: /^Acknowledge$/ })).toBeInTheDocument();
    expect(screen.getByText("Reviewed")).toBeInTheDocument();

    // Header badge indicates 1 Action Required
    expect(screen.getByText("1 Action Required")).toBeInTheDocument();
  });

  it("filters flags by unacknowledged and acknowledged status", async () => {
    vi.mocked(apiModule.api).mockResolvedValueOnce(mockFlags);

    render(
      <BrowserRouter>
        <FlagInbox />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText("Fitter (NSQF-L4-FIT)")).toBeInTheDocument();
    });

    // Click Unacknowledged filter button
    fireEvent.click(screen.getByRole("button", { name: /Unacknowledged \(1\)/i }));

    expect(screen.getByText("Fitter (NSQF-L4-FIT)")).toBeInTheDocument();
    expect(screen.queryByText("Welder (NSQF-L3-WLD)")).not.toBeInTheDocument();

    // Click Reviewed filter button
    fireEvent.click(screen.getByRole("button", { name: /Reviewed \(1\)/i }));

    expect(screen.queryByText("Fitter (NSQF-L4-FIT)")).not.toBeInTheDocument();
    expect(screen.getByText("Welder (NSQF-L3-WLD)")).toBeInTheDocument();
  });

  it("successfully acknowledges a flag and transitions card state to reviewed", async () => {
    vi.mocked(apiModule.api)
      .mockResolvedValueOnce(mockFlags) // initial fetch
      .mockResolvedValueOnce({
        acknowledged: true,
        acknowledged_at: "2026-09-18T12:00:00Z",
        acknowledged_by: "user-1",
        flag_id: "flag-1",
        message: "Flag acknowledged.",
      }); // post acknowledge

    render(
      <BrowserRouter>
        <FlagInbox />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /^Acknowledge$/ })).toBeInTheDocument();
    });

    const ackButton = screen.getByRole("button", { name: /^Acknowledge$/ });
    fireEvent.click(ackButton);

    await waitFor(() => {
      expect(apiModule.api).toHaveBeenCalledWith(
        "/institute/flags/flag-1/acknowledge",
        { method: "POST" }
      );
    });

    // Button should now transition to Reviewed
    await waitFor(() => {
      expect(screen.getAllByText("Reviewed")).toHaveLength(2);
    });
  });
});
