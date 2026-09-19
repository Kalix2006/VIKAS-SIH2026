import React from "react";
import { Link, NavLink, Route, Routes, useNavigate } from "react-router-dom";
import {
  ShieldCheck,
  ClipboardList,
  LogOut,
  UserCheck,
} from "lucide-react";
import { useAuth } from "../../lib/auth";
import { ReviewQueue } from "./ReviewQueue";
import { ReviewDetailView } from "./ReviewDetailView";

export const PanelLayout: React.FC = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  // Derive human readable role label
  const getRoleLabel = () => {
    const email = user?.email?.toLowerCase() || "";
    const name = user?.full_name?.toLowerCase() || "";
    if (email.includes("expert") || name.includes("academic") || name.includes("expert")) {
      return "Academic Expert (Veto-Eligible)";
    }
    if (email.includes("industry") || name.includes("industry")) {
      return "Industry Representative";
    }
    return "Program Lead (Governance)";
  };

  return (
    <div className="min-h-screen bg-slate-50/50 flex flex-col font-sans">
      {/* Top Navigation Bar */}
      <header className="sticky top-0 z-40 border-b border-slate-200 bg-white/95 backdrop-blur-md">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="flex h-16 items-center justify-between">
            {/* Logo and Platform Title */}
            <div className="flex items-center gap-4">
              <Link to="/panel" className="flex items-center gap-2.5">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-linear-to-tr from-emerald-700 to-teal-600 text-white shadow-md shadow-emerald-100">
                  <ShieldCheck className="h-5 w-5" />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-base font-black tracking-tight text-slate-900 block leading-tight">
                      VIKAS <span className="text-emerald-600 font-bold text-xs ml-1 tracking-wider uppercase">GOVERNANCE</span>
                    </span>
                  </div>
                  <span className="text-[10px] font-semibold text-slate-500 tracking-wider uppercase block">
                    Human-in-the-Loop Review Panel
                  </span>
                </div>
              </Link>
            </div>

            {/* Middle Nav Links */}
            <nav className="hidden md:flex items-center gap-1 text-sm font-semibold">
              <NavLink
                to="/panel"
                end
                className={({ isActive }) =>
                  `flex items-center gap-2 rounded-xl px-4 py-2 transition-colors ${
                    isActive
                      ? "bg-emerald-50 text-emerald-800 font-bold border border-emerald-200/50"
                      : "text-slate-600 hover:bg-slate-100/70 hover:text-slate-900"
                  }`
                }
              >
                <ClipboardList className="h-4 w-4" />
                Review Queue
              </NavLink>
            </nav>

            {/* Right User & Logout */}
            <div className="flex items-center gap-3">
              <div className="hidden sm:flex flex-col text-right">
                <div className="flex items-center justify-end gap-1.5">
                  <UserCheck className="w-3.5 h-3.5 text-emerald-600" />
                  <span className="text-xs font-bold text-slate-900 leading-tight">
                    {user?.full_name || "Panel Member"}
                  </span>
                </div>
                <span className="text-[10px] font-medium text-emerald-700 font-mono">
                  {getRoleLabel()}
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

        {/* Mobile Navigation Bar */}
        <div className="flex md:hidden border-t border-slate-100 px-4 py-1.5 bg-slate-50/80">
          <NavLink
            to="/panel"
            end
            className={({ isActive }) =>
              `flex-1 text-center py-2 text-xs font-bold rounded-lg transition-colors ${
                isActive ? "bg-white text-emerald-800 shadow-2xs border border-emerald-200" : "text-slate-600"
              }`
            }
          >
            Review Queue
          </NavLink>
        </div>
      </header>

      {/* Main Container */}
      <main className="mx-auto max-w-7xl flex-1 px-4 py-6 sm:px-6 lg:px-8 w-full">
        <Routes>
          <Route index element={<ReviewQueue />} />
          <Route path="reviews/:reviewId" element={<ReviewDetailView />} />
        </Routes>
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-200 bg-white py-4 text-center text-xs text-slate-400">
        VIKAS (Viksit India Kaushal Alignment System) • Independent Panel Governance • Auditable Algorithmic Decisions
      </footer>
    </div>
  );
};
export default PanelLayout;

