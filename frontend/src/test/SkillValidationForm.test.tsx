import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { BrowserRouter } from "react-router-dom";
import { SkillValidationForm } from "../routes/employer/SkillValidationForm";
import * as apiModule from "../lib/api";
import * as authModule from "../lib/auth";

vi.mock("../lib/api", () => ({
  api: vi.fn(),
}));

const mockInferredSkills = {
  trade_id: "trade-elec",
  trade_name: "Electrician",
  nsqf_code: "NSQF-L4-ELE",
  district_id: "dist-pune",
  district_name: "Pune",
  total_postings_analyzed: 45,
  inferred_skills: [
    {
      skill_name: "Industrial Control Panel Assembly",
      category: "technical_competency",
      posting_frequency: 18,
      is_recommended: true,
    },
    {
      skill_name: "Solar Rooftop On-Grid Inverter Wiring",
      category: "emerging",
      posting_frequency: 12,
      is_recommended: true,
    },
    {
      skill_name: "Multimeter & Megger Diagnostics",
      category: "core_tool",
      posting_frequency: 25,
      is_recommended: true,
    },
  ],
};

const mockValidationSuccess = {
  validation_id: "val-123",
  trade_name: "Electrician",
  district_name: "Pune",
  confirmed_skills: [
    "Industrial Control Panel Assembly",
    "Solar Rooftop On-Grid Inverter Wiring",
  ],
  extracted_from_free_text: ["PLC Ladder Logic"],
  parsed_by_llm: true,
  needs_manual_review: false,
  submitted_at: "2026-09-19T10:00:00Z",
};

describe("SkillValidationForm Component", () => {
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

  it("renders pre-filled inferred skills as interactive chips and submits under a minute", async () => {
    vi.mocked(apiModule.api).mockImplementation(async (path: string, options?: any) => {
      if (options?.method === "POST" && path === "/employer/validate") {
        return mockValidationSuccess;
      }
      if (path.includes("/employer/skills-inferred")) {
        return mockInferredSkills;
      }
      if (path.includes("/trainee/courses")) {
        return [
          { trade_id: "trade-elec", trade_name: "Electrician", nsqf_code: "NSQF-L4-ELE" },
        ];
      }
      throw new Error(`Unhandled path: ${path}`);
    });

    render(
      <BrowserRouter>
        <SkillValidationForm />
      </BrowserRouter>
    );

    // Verify speed promise banner
    expect(
      screen.getByText("One-Minute Industrial Skill Confirmation")
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Average Completion: 25 seconds/i)
    ).toBeInTheDocument();

    // Verify inferred skill chips are rendered
    await waitFor(() => {
      expect(
        screen.getByText("Industrial Control Panel Assembly")
      ).toBeInTheDocument();
      expect(
        screen.getByText("Solar Rooftop On-Grid Inverter Wiring")
      ).toBeInTheDocument();
      expect(
        screen.getByText("Multimeter & Megger Diagnostics")
      ).toBeInTheDocument();
    });

    // Toggle one skill off
    const solarChip = screen.getByText("Solar Rooftop On-Grid Inverter Wiring");
    fireEvent.click(solarChip);

    // Add a custom skill
    const customInput = screen.getByPlaceholderText(/Missing a specific tool\/skill\?/i);
    fireEvent.change(customInput, { target: { value: "SCADA HMI Configuration" } });
    const addBtn = screen.getByRole("button", { name: /Add Skill/i });
    fireEvent.click(addBtn);

    expect(screen.getByText("SCADA HMI Configuration")).toBeInTheDocument();

    // Open free text accordion and type requirement
    const accordionBtn = screen.getByRole("button", {
      name: /Have a Job Description or Free-Text Requirements\?/i,
    });
    fireEvent.click(accordionBtn);

    const textarea = screen.getByPlaceholderText(/e\.g\. We are expanding our Pune electric powertrain line/i);
    fireEvent.change(textarea, {
      target: { value: "Need high-voltage safety and PLC ladder logic skills." },
    });

    // Submit form
    const submitBtn = screen.getByRole("button", {
      name: /Confirm & Submit Skill Demand/i,
    });
    fireEvent.click(submitBtn);

    // Verify API called with appropriate payload
    await waitFor(() => {
      expect(apiModule.api).toHaveBeenCalledWith(
        "/employer/validate",
        expect.objectContaining({
          method: "POST",
          body: expect.stringContaining("SCADA HMI Configuration"),
        })
      );
    });

    // Verify confirmation feedback card
    await waitFor(() => {
      expect(screen.getByText(/Skill Validation Confirmed/i)).toBeInTheDocument();
      expect(screen.getByTestId("free-text-extracted")).toBeInTheDocument();
      expect(screen.getByTestId("extracted-skill-list")).toHaveTextContent("PLC Ladder Logic");
    });
  });
});
