import { useState, useEffect } from "react";
import { CheckCircle2, Briefcase, BarChart3, History, Sparkles, AlertCircle } from "lucide-react";
import { SkillValidationForm } from "./SkillValidationForm";
import { HiringSignalForm } from "./HiringSignalForm";
import { AggregateReadinessView } from "./AggregateReadinessView";
import { api } from "../../lib/api";

interface SubmissionItem {
  id: string;
  trade_name: string;
  district_name: string;
  type: string;
  summary: string;
  parsed_by_llm: boolean;
  needs_manual_review: boolean;
  submitted_at: string;
}

export function EmployerDashboard() {
  const [activeTab, setActiveTab] = useState<"validate" | "signal" | "readiness" | "history">("validate");
  const [history, setHistory] = useState<SubmissionItem[]>([]);
  const [loadingHistory, setLoadingHistory] = useState(false);

  const loadHistory = async () => {
    setLoadingHistory(true);
    try {
      const data = await api<SubmissionItem[]>("/employer/my-validations");
      setHistory(data);
    } catch {
      // Ignored if history fails to load
    } finally {
      setLoadingHistory(false);
    }
  };

  useEffect(() => {
    if (activeTab === "history") {
      loadHistory();
    }
  }, [activeTab]);

  return (
    <div className="space-y-6">
      {/* Navigation Tabs */}
      <div className="flex flex-wrap items-center gap-2 border-b border-slate-200 pb-3">
        <button
          type="button"
          onClick={() => setActiveTab("validate")}
          className={`flex items-center gap-2 rounded-lg px-4 py-2 text-xs font-bold transition-all ${
            activeTab === "validate"
              ? "bg-blue-600 text-white shadow-sm"
              : "bg-slate-100 text-slate-700 hover:bg-slate-200"
          }`}
        >
          <CheckCircle2 className="h-4 w-4" />
          One-Minute Skill Validation
        </button>

        <button
          type="button"
          onClick={() => setActiveTab("signal")}
          className={`flex items-center gap-2 rounded-lg px-4 py-2 text-xs font-bold transition-all ${
            activeTab === "signal"
              ? "bg-blue-600 text-white shadow-sm"
              : "bg-slate-100 text-slate-700 hover:bg-slate-200"
          }`}
        >
          <Briefcase className="h-4 w-4" />
          Signal Hiring Intent
        </button>

        <button
          type="button"
          onClick={() => setActiveTab("readiness")}
          className={`flex items-center gap-2 rounded-lg px-4 py-2 text-xs font-bold transition-all ${
            activeTab === "readiness"
              ? "bg-blue-600 text-white shadow-sm"
              : "bg-slate-100 text-slate-700 hover:bg-slate-200"
          }`}
        >
          <BarChart3 className="h-4 w-4" />
          Aggregate Cohort Readiness
        </button>

        <button
          type="button"
          onClick={() => setActiveTab("history")}
          className={`flex items-center gap-2 rounded-lg px-4 py-2 text-xs font-bold transition-all ${
            activeTab === "history"
              ? "bg-blue-600 text-white shadow-sm"
              : "bg-slate-100 text-slate-700 hover:bg-slate-200"
          }`}
        >
          <History className="h-4 w-4" />
          My Submissions History
        </button>
      </div>

      {/* Tab Panels */}
      {activeTab === "validate" && <SkillValidationForm />}
      {activeTab === "signal" && <HiringSignalForm />}
      {activeTab === "readiness" && <AggregateReadinessView />}

      {activeTab === "history" && (
        <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-sm font-bold text-slate-900">Your Past Validations & Hiring Signals</h2>
              <p className="text-xs text-slate-500">
                Submissions scoped strictly to your employer account. Planners integrate these directly into district capacity models.
              </p>
            </div>
            <button
              type="button"
              onClick={loadHistory}
              className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-100"
            >
              Refresh
            </button>
          </div>

          {loadingHistory ? (
            <div className="py-12 text-center text-xs text-slate-400">Loading your submissions...</div>
          ) : history.length === 0 ? (
            <div className="rounded-lg border border-dashed border-slate-200 p-8 text-center text-xs text-slate-500">
              No validations submitted yet. Use the "One-Minute Skill Validation" tab to record your current hiring expectations.
            </div>
          ) : (
            <div className="divide-y divide-slate-100">
              {history.map((item) => (
                <div key={item.id} className="py-3 flex items-center justify-between gap-4">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-bold text-slate-900">{item.trade_name}</span>
                      <span className="text-[11px] text-slate-500">• {item.district_name}</span>
                      <span
                        className={`rounded px-1.5 py-0.5 text-[10px] font-semibold ${
                          item.type === "hiring_signal"
                            ? "bg-purple-100 text-purple-800"
                            : "bg-blue-100 text-blue-800"
                        }`}
                      >
                        {item.type === "hiring_signal" ? "Hiring Intent" : "Skill Validation"}
                      </span>
                      {item.parsed_by_llm && (
                        <span className="flex items-center gap-1 rounded bg-purple-50 border border-purple-200 px-1.5 py-0.5 text-[10px] font-semibold text-purple-700">
                          <Sparkles className="h-3 w-3" />
                          AI Parsed
                        </span>
                      )}
                      {item.needs_manual_review && (
                        <span className="flex items-center gap-1 rounded bg-amber-50 border border-amber-200 px-1.5 py-0.5 text-[10px] font-semibold text-amber-700">
                          <AlertCircle className="h-3 w-3" />
                          Manual Review Flag
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-slate-600">{item.summary}</p>
                  </div>
                  <div className="text-[11px] text-slate-400 shrink-0">
                    {new Date(item.submitted_at).toLocaleDateString("en-IN", {
                      day: "numeric",
                      month: "short",
                      year: "numeric",
                    })}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
