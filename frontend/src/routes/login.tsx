import React, { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../lib/auth";
import { Sparkles, ArrowRight, ShieldCheck, UserCheck } from "lucide-react";

export function LoginRoute() {
  const {
    login,
    quickLoginAsTrainee,
    quickLoginAsInstituteAdmin,
    quickLoginAsPanelMember,
    quickLoginAsPlanner,
    quickLoginAsEmployer,
  } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const from =
    (location.state as { from?: { pathname: string } })?.from?.pathname ||
    "/trainee";

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const user = await login(email, password);
      if (user.role === "trainee") {
        navigate(from, { replace: true });
      } else {
        navigate(`/${user.role}`, { replace: true });
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to sign in");
    } finally {
      setLoading(false);
    }
  };

  const handleQuickLogin = async (role: string, customEmail?: string) => {
    setError(null);
    setLoading(true);
    try {
      if (role === "trainee") {
        await quickLoginAsTrainee();
        navigate("/trainee", { replace: true });
      } else if (role === "institute") {
        await quickLoginAsInstituteAdmin();
        navigate("/institute", { replace: true });
      } else if (role === "panel") {
        await quickLoginAsPanelMember(customEmail);
        navigate("/panel", { replace: true });
      } else if (role === "planner") {
        await quickLoginAsPlanner();
        navigate("/planner", { replace: true });
      } else if (role === "employer") {
        await quickLoginAsEmployer();
        navigate("/employer", { replace: true });
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to sign in demo account");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-b from-slate-50 to-slate-100 p-4 font-sans">
      <div className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-6 shadow-xl sm:p-8">
        <div className="text-center">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-xl bg-emerald-600 text-white shadow-md shadow-emerald-200">
            <ShieldCheck className="h-6 w-6" />
          </div>
          <h1 className="mt-4 text-2xl font-bold tracking-tight text-slate-900">
            VIKAS Platform
          </h1>
          <p className="mt-1 text-xs font-semibold uppercase tracking-wider text-emerald-700">
            Viksit India Kaushal Alignment System
          </p>
          <p className="mt-2 text-sm text-slate-500">
            Sign in to access your district skilling catalog & AI advisor
          </p>
        </div>

        {error && (
          <div className="mt-6 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="mt-6 space-y-4">
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-700">
              Official Email Address
            </label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="e.g. trainee@vikas.gov.in"
              className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm shadow-sm focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-700">
              Password
            </label>
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm shadow-sm focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="flex w-full items-center justify-center gap-2 rounded-lg bg-emerald-600 py-2.5 text-sm font-semibold text-white shadow-md shadow-emerald-100 hover:bg-emerald-700 disabled:opacity-50"
          >
            {loading ? "Signing in..." : "Sign In"}
            <ArrowRight className="h-4 w-4" />
          </button>
        </form>

        <div className="relative my-6">
          <div className="absolute inset-0 flex items-center">
            <div className="w-full border-t border-slate-200" />
          </div>
          <div className="relative flex justify-center text-xs uppercase">
            <span className="bg-white px-2 text-slate-400 font-medium">
              Demo Evaluation Accounts
            </span>
          </div>
        </div>

        <div className="flex flex-col gap-2">
          <button
            type="button"
            onClick={() => handleQuickLogin("trainee")}
            disabled={loading}
            className="flex w-full items-center justify-center gap-2 rounded-lg border border-emerald-200 bg-emerald-50/70 py-2 text-xs font-semibold text-emerald-800 hover:bg-emerald-100 hover:border-emerald-300 transition-colors disabled:opacity-50"
          >
            <Sparkles className="h-3.5 w-3.5 text-emerald-600" />
            Quick-login as Trainee (Pune)
          </button>

          <button
            type="button"
            onClick={() => handleQuickLogin("institute")}
            disabled={loading}
            className="flex w-full items-center justify-center gap-2 rounded-lg border border-indigo-200 bg-indigo-50/70 py-2 text-xs font-semibold text-indigo-800 hover:bg-indigo-100 hover:border-indigo-300 transition-colors disabled:opacity-50"
          >
            <Sparkles className="h-3.5 w-3.5 text-indigo-600" />
            Quick-login as Institute Admin (ITI Pune)
          </button>

          <button
            type="button"
            onClick={() => handleQuickLogin("planner")}
            disabled={loading}
            className="flex w-full items-center justify-center gap-2 rounded-lg border border-amber-200 bg-amber-50/70 py-2 text-xs font-semibold text-amber-900 hover:bg-amber-100 hover:border-amber-300 transition-colors disabled:opacity-50"
          >
            <Sparkles className="h-3.5 w-3.5 text-amber-600" />
            Quick-login as District Skill Officer (Planner)
          </button>

          <button
            type="button"
            onClick={() => handleQuickLogin("employer")}
            disabled={loading}
            className="flex w-full items-center justify-center gap-2 rounded-lg border border-blue-200 bg-blue-50/70 py-2 text-xs font-semibold text-blue-900 hover:bg-blue-100 hover:border-blue-300 transition-colors disabled:opacity-50"
          >
            <Sparkles className="h-3.5 w-3.5 text-blue-600" />
            Quick-login as Industry Partner / Employer (Tata/Mahindra)
          </button>

          <div className="grid grid-cols-2 gap-2 pt-1">
            <button
              type="button"
              onClick={() => handleQuickLogin("panel", "panel@demo.vikas")}
              disabled={loading}
              className="flex items-center justify-center gap-1.5 rounded-lg border border-purple-200 bg-purple-50/70 py-2 text-[11px] font-semibold text-purple-800 hover:bg-purple-100 transition-colors disabled:opacity-50"
            >
              <UserCheck className="h-3.5 w-3.5 text-purple-600" />
              Academic Expert
            </button>

            <button
              type="button"
              onClick={() => handleQuickLogin("panel", "panel_lead@demo.vikas")}
              disabled={loading}
              className="flex items-center justify-center gap-1.5 rounded-lg border border-slate-200 bg-slate-50 py-2 text-[11px] font-semibold text-slate-800 hover:bg-slate-100 transition-colors disabled:opacity-50"
            >
              <UserCheck className="h-3.5 w-3.5 text-slate-600" />
              Panel Lead
            </button>
          </div>
        </div>

        <p className="mt-6 text-center text-xs text-slate-400">
          Government of India • Ministry of Skill Development and Entrepreneurship
        </p>
      </div>
    </div>
  );
}
