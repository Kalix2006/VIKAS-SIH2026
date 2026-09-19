import { Outlet, useNavigate } from "react-router-dom";
import { Building2, LogOut, ShieldCheck, MapPin } from "lucide-react";
import { useAuth } from "../../lib/auth";

export function EmployerLayout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 font-sans">
      {/* Executive Top Navigation Header */}
      <header className="sticky top-0 z-30 border-b border-slate-200 bg-white shadow-xs">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3 sm:px-6 lg:px-8">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-600 text-white shadow-sm shadow-blue-200">
              <Building2 className="h-5 w-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-base font-black tracking-tight text-slate-900">VIKAS</span>
                <span className="rounded-md bg-blue-100 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-blue-800">
                  Industry Partner Portal
                </span>
              </div>
              <p className="text-[11px] text-slate-500 font-medium">
                Viksit India Kaushal Alignment System • Demand Calibration & Hiring Signals
              </p>
            </div>
          </div>

          <div className="flex items-center gap-4">
            <div className="hidden md:flex items-center gap-2 rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs font-semibold text-slate-700">
              <MapPin className="h-3.5 w-3.5 text-blue-600" />
              <span>Pune District Cluster</span>
            </div>

            <div className="flex items-center gap-3 pl-3 border-l border-slate-200">
              <div className="text-right hidden sm:block">
                <div className="text-xs font-bold text-slate-800">{user?.full_name || "Industrial Employer"}</div>
                <div className="text-[10px] text-blue-600 font-semibold uppercase tracking-wider">
                  Employer (Manufacturing / Auto)
                </div>
              </div>

              <button
                type="button"
                onClick={handleLogout}
                className="flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-xs font-semibold text-slate-600 hover:bg-slate-100 hover:text-slate-900 transition-colors"
                title="Sign out"
              >
                <LogOut className="h-3.5 w-3.5" />
                <span className="hidden sm:inline">Sign Out</span>
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content Body */}
      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <Outlet />
      </main>

      <footer className="border-t border-slate-200 bg-white py-6 text-center text-xs text-slate-500">
        <div className="flex items-center justify-center gap-2 text-slate-600 font-medium">
          <ShieldCheck className="h-4 w-4 text-emerald-600" />
          <span>Government of India • Ministry of Skill Development and Entrepreneurship (MSDE)</span>
        </div>
        <p className="mt-1 text-[11px] text-slate-400">
          Industry demand telemetry directly calibrates district NSQF training quotas and institute equipment investments.
        </p>
      </footer>
    </div>
  );
}

