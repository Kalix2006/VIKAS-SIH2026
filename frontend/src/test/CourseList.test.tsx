import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { CourseList, TraineeCourse } from "../routes/trainee/CourseList";
import * as apiModule from "../lib/api";

vi.mock("../lib/api", () => ({
  api: vi.fn(),
}));

const mockCourses: TraineeCourse[] = [
  {
    id: "course-1",
    institute_id: "inst-1",
    institute_name: "Government ITI Pune",
    trade_id: "trade-1",
    trade_name: "Electrician",
    nsqf_code: "ELE/Q0101",
    seats_available: 24,
    status: "active",
    demand_label: "Strong local demand",
    demand_level: "high",
    has_alternatives: false,
  },
  {
    id: "course-2",
    institute_id: "inst-1",
    institute_name: "Government ITI Pune",
    trade_id: "trade-2",
    trade_name: "Fitter",
    nsqf_code: "CSC/Q0901",
    seats_available: 12,
    status: "flagged",
    demand_label: "Evolving industry skills",
    demand_level: "stable",
    has_alternatives: true,
  },
];

describe("CourseList Component", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders courses with plain-language demand labels and badges", async () => {
    vi.mocked(apiModule.api).mockResolvedValueOnce(mockCourses);

    render(<CourseList />);

    await waitFor(() => {
      expect(screen.getByText("Electrician")).toBeInTheDocument();
      expect(screen.getByText("Fitter")).toBeInTheDocument();
    });

    // Check plain language demand labels
    expect(screen.getByText("Strong local demand")).toBeInTheDocument();
    expect(screen.getByText("Evolving industry skills")).toBeInTheDocument();

    // Verify seats and institutes
    expect(screen.getByText("24 open seats")).toBeInTheDocument();
    expect(screen.getByText("12 open seats")).toBeInTheDocument();
  });

  it("shows 'View Recommended Alternatives' button ONLY for flagged courses", async () => {
    vi.mocked(apiModule.api).mockResolvedValueOnce(mockCourses);
    const onSelectAlternatives = vi.fn();

    render(<CourseList onSelectCourseAlternatives={onSelectAlternatives} />);

    await waitFor(() => {
      expect(screen.getByText("Electrician")).toBeInTheDocument();
    });

    // Course 1 is active: should show Direct Enrollment Open
    expect(screen.getByText("Direct Enrollment Open")).toBeInTheDocument();

    // Course 2 is flagged: should show Modernization Advisory and View Recommended Alternatives button
    expect(screen.getByText("Modernization Advisory")).toBeInTheDocument();
    const altButtons = screen.getAllByTestId("view-alternatives-btn");
    expect(altButtons).toHaveLength(1);

    // Clicking alternative button triggers callback with course-2
    fireEvent.click(altButtons[0]!);
    expect(onSelectAlternatives).toHaveBeenCalledWith("course-2");
  });
});
