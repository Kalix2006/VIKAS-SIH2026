import React, { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../lib/auth";
import { Sparkles, ArrowRight, UserCheck, Shield } from "lucide-react";
import { ThemeToggle } from "../components/ThemeToggle";

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
    <div className="relative min-h-screen flex items-center justify-center p-4 font-sans bg-[#060913] text-slate-100 overflow-hidden">
      {/* Ambient background neon glow effects */}
      <div className="pointer-events-none absolute -top-40 -left-40 h-96 w-96 rounded-full bg-cyan-500/10 blur-[120px]" />
      <div className="pointer-events-none absolute -bottom-40 -right-40 h-96 w-96 rounded-full bg-indigo-500/15 blur-[140px]" />
      <div className="pointer-events-none absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 h-80 w-80 rounded-full bg-emerald-500/10 blur-[130px]" />

      {/* Floating ThemeToggle in Top-Right */}
      <div className="absolute top-4 right-4 z-50 flex items-center gap-2 rounded-full border border-cyan-500/30 bg-[#0b1120]/80 px-3 py-1.5 backdrop-blur-md shadow-[0_0_15px_rgba(6,182,212,0.2)]">
        <span className="text-[10px] font-mono uppercase tracking-wider text-cyan-400">Theme</span>
        <ThemeToggle className="!h-7 !w-7 !rounded-full !border-cyan-500/40 !bg-cyan-950/40 !text-cyan-300 hover:!border-cyan-400" />
      </div>

      {/* Main Glassmorphism Neon Card */}
      <div className="relative z-10 w-full max-w-md rounded-2xl border border-cyan-500/40 bg-[#0b1120]/90 p-6 shadow-[0_0_40px_rgba(6,182,212,0.18)] backdrop-blur-xl sm:p-8 overflow-hidden">
        {/* Neon top accent line */}
        <div className="absolute top-0 left-0 right-0 h-[2px] bg-gradient-to-r from-emerald-400 via-cyan-400 to-indigo-500 shadow-[0_0_12px_rgba(6,182,212,0.8)]" />

        {/* Logo and Header */}
        <div className="text-center">
          <div className="mx-auto flex h-20 w-20 items-center justify-center rounded-2xl border border-cyan-400/50 bg-[#060913] p-1.5 shadow-[0_0_25px_rgba(6,182,212,0.3)]">
            <img
              src="/vikas-logo.jpg"
              alt="VIKAS Logo"
              className="h-full w-full rounded-xl object-contain"
            />
          </div>
          <h1 className="mt-4 text-2xl font-black tracking-tight text-white flex items-center justify-center gap-2">
            VIKAS Platform
          </h1>
          <p className="mt-1 text-xs font-bold uppercase tracking-wider text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-emerald-400">
            Viksit India Kaushal Alignment System
          </p>
          <p className="mt-1.5 text-xs text-slate-400">
            Sign in to access your district skilling catalog & AI advisor
          </p>
        </div>

        {error && (
          <div className="mt-5 rounded-xl border border-red-500/40 bg-red-950/40 p-3 text-xs font-medium text-red-300 shadow-[0_0_15px_rgba(239,68,68,0.2)]">
            {error}
          </div>
        )}

        {/* Credentials Form */}
        <form onSubmit={handleSubmit} className="mt-5 space-y-3.5">
          <div>
            <label className="block text-[11px] font-bold uppercase tracking-wider text-slate-300">
              Official Email Address
            </label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="e.g. trainee@vikas.gov.in"
              className="mt-1 block w-full rounded-xl border border-slate-700/80 bg-[#060913]/90 px-3.5 py-2.5 text-sm text-white placeholder-slate-500 shadow-inner transition-all focus:border-cyan-400 focus:outline-none focus:ring-1 focus:ring-cyan-400 focus:shadow-[0_0_15px_rgba(6,182,212,0.4)]"
            />
          </div>

          <div>
            <label className="block text-[11px] font-bold uppercase tracking-wider text-slate-300">
              Password
            </label>
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              className="mt-1 block w-full rounded-xl border border-slate-700/80 bg-[#060913]/90 px-3.5 py-2.5 text-sm text-white placeholder-slate-500 shadow-inner transition-all focus:border-cyan-400 focus:outline-none focus:ring-1 focus:ring-cyan-400 focus:shadow-[0_0_15px_rgba(6,182,212,0.4)]"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="flex w-full items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-cyan-500 via-teal-500 to-emerald-500 py-2.5 text-sm font-bold text-slate-950 shadow-[0_0_20px_rgba(6,182,212,0.4)] transition-all hover:brightness-110 hover:shadow-[0_0_25px_rgba(6,182,212,0.6)] disabled:opacity-50"
          >
            {loading ? "Signing in..." : "Sign In"}
            <ArrowRight className="h-4 w-4" />
          </button>
        </form>

        {/* Demo Divider with Neon Pill */}
        <div className="relative my-5">
          <div className="absolute inset-0 flex items-center">
            <div className="w-full border-t border-slate-800" />
          </div>
          <div className="relative flex justify-center text-xs uppercase">
            <span className="rounded-full border border-cyan-500/30 bg-[#0b1120] px-3 py-0.5 text-[10px] font-mono tracking-wider text-cyan-400 shadow-[0_0_10px_rgba(6,182,212,0.15)]">
              Demo Evaluation Accounts
            </span>
          </div>
        </div>

        {/* Quick Login Buttons with Neon Borders */}
        <div className="flex flex-col gap-2">
          <button
            type="button"
            onClick={() => handleQuickLogin("trainee")}
            disabled={loading}
            className="group flex w-full items-center justify-between rounded-xl border border-emerald-500/40 bg-emerald-950/25 px-3.5 py-2 text-xs font-semibold text-emerald-300 shadow-[0_0_10px_rgba(16,185,129,0.1)] transition-all hover:border-emerald-400 hover:bg-emerald-900/35 hover:shadow-[0_0_18px_rgba(16,185,129,0.35)] disabled:opacity-50"
          >
            <div className="flex items-center gap-2">
              <Sparkles className="h-3.5 w-3.5 text-emerald-400 transition-transform group-hover:scale-110" />
              <span>Quick-login as Trainee (Pune)</span>
            </div>
            <span className="rounded border border-emerald-500/30 bg-emerald-950/60 px-1.5 py-0.5 text-[10px] font-mono uppercase tracking-wider text-emerald-400">
              Go
            </span>
          </button>

          <button
            type="button"
            onClick={() => handleQuickLogin("institute")}
            disabled={loading}
            className="group flex w-full items-center justify-between rounded-xl border border-indigo-500/40 bg-indigo-950/25 px-3.5 py-2 text-xs font-semibold text-indigo-300 shadow-[0_0_10px_rgba(99,102,241,0.1)] transition-all hover:border-indigo-400 hover:bg-indigo-900/35 hover:shadow-[0_0_18px_rgba(99,102,241,0.35)] disabled:opacity-50"
          >
            <div className="flex items-center gap-2">
              <Sparkles className="h-3.5 w-3.5 text-indigo-400 transition-transform group-hover:scale-110" />
              <span>Quick-login as Institute Admin (ITI Pune)</span>
            </div>
            <span className="rounded border border-indigo-500/30 bg-indigo-950/60 px-1.5 py-0.5 text-[10px] font-mono uppercase tracking-wider text-indigo-400">
              Go
            </span>
          </button>

          <button
            type="button"
            onClick={() => handleQuickLogin("planner")}
            disabled={loading}
            className="group flex w-full items-center justify-between rounded-xl border border-amber-500/40 bg-amber-950/25 px-3.5 py-2 text-xs font-semibold text-amber-300 shadow-[0_0_10px_rgba(245,158,11,0.1)] transition-all hover:border-amber-400 hover:bg-amber-900/35 hover:shadow-[0_0_18px_rgba(245,158,11,0.35)] disabled:opacity-50"
          >
            <div className="flex items-center gap-2">
              <Sparkles className="h-3.5 w-3.5 text-amber-400 transition-transform group-hover:scale-110" />
              <span>Quick-login as District Skill Officer (Planner)</span>
            </div>
            <span className="rounded border border-amber-500/30 bg-amber-950/60 px-1.5 py-0.5 text-[10px] font-mono uppercase tracking-wider text-amber-400">
              Go
            </span>
          </button>

          <button
            type="button"
            onClick={() => handleQuickLogin("employer")}
            disabled={loading}
            className="group flex w-full items-center justify-between rounded-xl border border-cyan-500/40 bg-cyan-950/25 px-3.5 py-2 text-xs font-semibold text-cyan-300 shadow-[0_0_10px_rgba(6,182,212,0.1)] transition-all hover:border-cyan-400 hover:bg-cyan-900/35 hover:shadow-[0_0_18px_rgba(6,182,212,0.35)] disabled:opacity-50"
          >
            <div className="flex items-center gap-2">
              <Sparkles className="h-3.5 w-3.5 text-cyan-400 transition-transform group-hover:scale-110" />
              <span>Quick-login as Industry Partner / Employer (Tata/Mahindra)</span>
            </div>
            <span className="rounded border border-cyan-500/30 bg-cyan-950/60 px-1.5 py-0.5 text-[10px] font-mono uppercase tracking-wider text-cyan-400">
              Go
            </span>
          </button>

          <div className="grid grid-cols-2 gap-2 pt-0.5">
            <button
              type="button"
              onClick={() => handleQuickLogin("panel", "panel@demo.vikas")}
              disabled={loading}
              className="flex items-center justify-center gap-1.5 rounded-xl border border-purple-500/40 bg-purple-950/25 py-2 text-[11px] font-semibold text-purple-300 shadow-[0_0_10px_rgba(168,85,247,0.1)] transition-all hover:border-purple-400 hover:bg-purple-900/35 hover:shadow-[0_0_18px_rgba(168,85,247,0.35)] disabled:opacity-50"
            >
              <UserCheck className="h-3.5 w-3.5 text-purple-400" />
              Academic Expert
            </button>

            <button
              type="button"
              onClick={() => handleQuickLogin("panel", "panel_lead@demo.vikas")}
              disabled={loading}
              className="flex items-center justify-center gap-1.5 rounded-xl border border-teal-500/40 bg-teal-950/25 py-2 text-[11px] font-semibold text-teal-300 shadow-[0_0_10px_rgba(20,184,166,0.1)] transition-all hover:border-teal-400 hover:bg-teal-900/35 hover:shadow-[0_0_18px_rgba(20,184,166,0.35)] disabled:opacity-50"
            >
              <UserCheck className="h-3.5 w-3.5 text-teal-400" />
              Panel Lead
            </button>
          </div>
        </div>

        {/* Footer */}
        <div className="mt-5 flex items-center justify-center gap-1.5 text-center text-[10px] text-slate-500">
          <Shield className="h-3 w-3 text-cyan-500/70" />
          <span>Government of India • Ministry of Skill Development and Entrepreneurship</span>
        </div>
      </div>
    </div>
  );
}

