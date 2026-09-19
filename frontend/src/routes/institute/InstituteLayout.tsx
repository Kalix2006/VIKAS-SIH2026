import React from "react";
import { Link, NavLink, Route, Routes, useNavigate } from "react-router-dom";
import {
  Building2,
  CheckSquare,
  BarChart2,
  LogOut,
} from "lucide-react";
import { useAuth } from "../../lib/auth";
import { FlagInbox } from "./FlagInbox";
import { DriftDetailView } from "./DriftDetailView";
import { EnrollmentVsDemandView } from "./EnrollmentVsDemandView";

export const InstituteLayout: React.FC = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <div className="min-h-screen bg-slate-50/50 flex flex-col font-sans">
      {/* Top Navigation Bar */}
      <header className="sticky top-0 z-40 border-b border-slate-200 bg-white/95 backdrop-blur-md">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="flex h-16 items-center justify-between">
            {/* Logo and Platform Title */}
            <div className="flex items-center gap-4">
              <Link to="/institute" className="flex items-center gap-2.5">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-linear-to-tr from-indigo-700 to-indigo-500 text-white shadow-md shadow-indigo-100">
                  <Building2 className="h-5 w-5" />
                </div>
                <div>
                  <span className="text-base font-black tracking-tight text-slate-900 block leading-tight">
                    VIKAS <span className="text-indigo-600 font-medium text-xs ml-1">INSTITUTE</span>
                  </span>
                  <span className="text-[10px] font-semibold text-slate-500 tracking-wider uppercase block">
                    Institutional Governance Portal
                  </span>
                </div>
              </Link>
            </div>

            {/* Middle Nav Links */}
            <nav className="hidden md:flex items-center gap-1 text-sm font-semibold">
              <NavLink
                to="/institute"
                end
                className={({ isActive }) =>
                  `flex items-center gap-2 rounded-xl px-4 py-2 transition-colors ${
                    isActive
                      ? "bg-indigo-50 text-indigo-700 font-bold"
                      : "text-slate-600 hover:bg-slate-100/70 hover:text-slate-900"
                  }`
                }
              >
                <CheckSquare className="h-4 w-4" />
                Flag Inbox
              </NavLink>

              <NavLink
                to="/institute/enrollment-vs-demand"
                className={({ isActive }) =>
                  `flex items-center gap-2 rounded-xl px-4 py-2 transition-colors ${
                    isActive
                      ? "bg-indigo-50 text-indigo-700 font-bold"
                      : "text-slate-600 hover:bg-slate-100/70 hover:text-slate-900"
                  }`
                }
              >
                <BarChart2 className="h-4 w-4" />
                Enrollment vs. Demand
              </NavLink>
            </nav>

            {/* Right User & Logout */}
            <div className="flex items-center gap-3">
              <div className="hidden sm:flex flex-col text-right">
                <span className="text-xs font-bold text-slate-900 leading-tight">
                  {user?.full_name || "Principal (Admin)"}
                </span>
                <span className="text-[10px] font-medium text-slate-500">
                  Institute Administrator
                </span>
              </div>

              <button
                onClick={handleLogout}
                className="flex items-center gap-1.5 rounded-xl border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50 hover:text-rose-600 transition-colors shadow-2xs"
              >
                <LogOut className="h-3.5 w-3.5" />
                <span className="hidden sm:inline">Logout</span>
              </button>
            </div>
          </div>
        </div>

        {/* Mobile Navigation Tabs */}
        <div className="flex md:hidden border-t border-slate-100 px-4 py-1.5 bg-slate-50/80">
          <NavLink
            to="/institute"
            end
            className={({ isActive }) =>
              `flex-1 text-center py-2 text-xs font-bold rounded-lg transition-colors ${
                isActive ? "bg-white text-indigo-700 shadow-2xs" : "text-slate-600"
              }`
            }
          >
            Flag Inbox
          </NavLink>
          <NavLink
            to="/institute/enrollment-vs-demand"
            className={({ isActive }) =>
              `flex-1 text-center py-2 text-xs font-bold rounded-lg transition-colors ${
                isActive ? "bg-white text-indigo-700 shadow-2xs" : "text-slate-600"
              }`
            }
          >
            Enrollment vs Demand
          </NavLink>
        </div>
      </header>

      {/* Main Container */}
      <main className="mx-auto max-w-7xl flex-1 px-4 py-6 sm:px-6 lg:px-8 w-full">
        <Routes>
          <Route index element={<FlagInbox />} />
          <Route path="flags/:flagId/detail" element={<DriftDetailView />} />
          <Route path="enrollment-vs-demand" element={<EnrollmentVsDemandView />} />
        </Routes>
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-200 bg-white py-4 text-center text-xs text-slate-400">
        VIKAS (Viksit India Kaushal Alignment System) • Institute Administration
      </footer>
    </div>
  );
};
