import React from "react";
import { Link, NavLink, Route, Routes, useNavigate } from "react-router-dom";
import {
  Map,
  ArrowLeftRight,
  LogOut,
} from "lucide-react";
import { ThemeToggle } from "../../components/ThemeToggle";
import { useAuth } from "../../lib/auth";
import { DistrictMap } from "./DistrictMap";
import { DistrictDrillDown } from "./DistrictDrillDown";
import { DistrictCompare } from "./DistrictCompare";

export const PlannerLayout: React.FC = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <div className="min-h-screen bg-slate-50/50 dark:bg-[#060913] text-slate-900 dark:text-slate-100 flex flex-col font-sans">
      {/* Top Navigation Bar with Neon Accent */}
      <header className="sticky top-0 z-40 border-b border-slate-200 dark:border-amber-500/30 bg-white/95 dark:bg-[#0b1120]/95 backdrop-blur-md dark:shadow-[0_4px_25px_rgba(0,0,0,0.8),0_1px_15px_rgba(245,158,11,0.2)]">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="flex h-16 items-center justify-between">
            {/* Logo and Platform Title */}
            <div className="flex items-center gap-4">
              <Link to="/planner" className="flex items-center gap-2.5">
                <img src="/vikas-logo.jpg" alt="VIKAS" className="h-10 w-10 rounded-xl object-contain" />
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-base font-black tracking-tight text-slate-900 block leading-tight">
                      VIKAS <span className="text-amber-600 font-bold text-xs ml-1 tracking-wider uppercase">PLANNER</span>
                    </span>
                  </div>
                  <span className="text-[10px] font-semibold text-slate-500 tracking-wider uppercase block">
                    District Alignment & Capacity Dashboard
                  </span>
                </div>
              </Link>
            </div>

            {/* Middle Nav Links */}
            <nav className="hidden md:flex items-center gap-1 text-sm font-semibold">
              <NavLink
                to="/planner"
                end
                className={({ isActive }) =>
                  `flex items-center gap-2 rounded-xl px-4 py-2 transition-colors ${
                    isActive
                      ? "bg-amber-50 text-amber-900 font-bold border border-amber-200/60"
                      : "text-slate-600 hover:bg-slate-100/70 hover:text-slate-900"
                  }`
                }
              >
                <Map className="h-4 w-4 text-amber-600" />
                Geographic Heatmap
              </NavLink>

              <NavLink
                to="/planner/compare"
                className={({ isActive }) =>
                  `flex items-center gap-2 rounded-xl px-4 py-2 transition-colors ${
                    isActive
                      ? "bg-amber-50 text-amber-900 font-bold border border-amber-200/60"
                      : "text-slate-600 hover:bg-slate-100/70 hover:text-slate-900"
                  }`
                }
              >
                <ArrowLeftRight className="h-4 w-4 text-indigo-600" />
                Trade Benchmarking
              </NavLink>
            </nav>

            {/* Right User & Logout */}
            <div className="flex items-center gap-3">
              <div className="hidden sm:flex flex-col text-right">
                <span className="text-xs font-bold text-slate-900 leading-tight">
                  {user?.full_name || "District Skill Officer"}
                </span>
                <span className="text-[10px] font-medium text-amber-800">
                  State & District Planner
                </span>
              </div>

              <ThemeToggle />

              <button
                onClick={handleLogout}
                className="flex items-center gap-1.5 rounded-xl border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50 hover:text-rose-600 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700 dark:hover:text-rose-400 transition-colors shadow-2xs"
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
            to="/planner"
            end
            className={({ isActive }) =>
              `flex-1 text-center py-2 text-xs font-bold rounded-lg transition-colors ${
                isActive ? "bg-white text-amber-900 shadow-2xs border border-amber-200" : "text-slate-600"
              }`
            }
          >
            Heatmap
          </NavLink>
          <NavLink
            to="/planner/compare"
            className={({ isActive }) =>
              `flex-1 text-center py-2 text-xs font-bold rounded-lg transition-colors ${
                isActive ? "bg-white text-amber-900 shadow-2xs border border-amber-200" : "text-slate-600"
              }`
            }
          >
            Compare
          </NavLink>
        </div>
      </header>

      {/* Main Container */}
      <main className="mx-auto max-w-7xl flex-1 px-4 py-6 sm:px-6 lg:px-8 w-full">
        <Routes>
          <Route index element={<DistrictMap />} />
          <Route path="districts/:districtId" element={<DistrictDrillDown />} />
          <Route path="compare" element={<DistrictCompare />} />
        </Routes>
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-200 bg-white py-4 text-center text-xs text-slate-400">
        VIKAS (Viksit India Kaushal Alignment System) • Strategic Planning & District Resource Optimization
      </footer>
    </div>
  );
};
export default PlannerLayout;
