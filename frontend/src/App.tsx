import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, RequireRole } from "./lib/auth";
import { LoginRoute } from "./routes/login";
import { TraineeLayout } from "./routes/trainee/TraineeLayout";
import { InstituteLayout } from "./routes/institute/InstituteLayout";
import { PanelLayout } from "./routes/panel/PanelLayout";
import { PlannerLayout } from "./routes/planner/PlannerLayout";
import { EmployerLayout } from "./routes/employer/EmployerLayout";
import { EmployerDashboard } from "./routes/employer/EmployerDashboard";

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          {/* Public Login Route */}
          <Route path="/login" element={<LoginRoute />} />

          {/* Protected Trainee Portal */}
          <Route
            path="/trainee/*"
            element={
              <RequireRole role="trainee">
                <TraineeLayout />
              </RequireRole>
            }
          />

          {/* Protected Institute Admin Portal */}
          <Route
            path="/institute/*"
            element={
              <RequireRole role="institute_admin">
                <InstituteLayout />
              </RequireRole>
            }
          />

          {/* Protected Panel Member Governance Portal */}
          <Route
            path="/panel/*"
            element={
              <RequireRole role="panel_member">
                <PanelLayout />
              </RequireRole>
            }
          />

          {/* Protected State & District Planner Portal */}
          <Route
            path="/planner/*"
            element={
              <RequireRole role="planner">
                <PlannerLayout />
              </RequireRole>
            }
          />

          {/* Protected Industry Partner / Employer Portal */}
          <Route
            path="/employer/*"
            element={
              <RequireRole role="employer">
                <EmployerLayout />
              </RequireRole>
            }
          >
            <Route index element={<EmployerDashboard />} />
          </Route>

          {/* Default redirect to login or trainee portal */}
          <Route path="*" element={<Navigate to="/login" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}
