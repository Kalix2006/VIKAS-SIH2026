import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import App from "../App";

describe("App", () => {
  it("redirects unauthenticated visitors to login route", () => {
    render(<App />);
    expect(screen.getByText("VIKAS Platform")).toBeInTheDocument();
    expect(
      screen.getByText("Viksit India Kaushal Alignment System")
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Quick-login as Trainee \(Pune\)/i)
    ).toBeInTheDocument();
  });
});
