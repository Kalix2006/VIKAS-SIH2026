import { useEffect, useState } from "react";
import { api } from "../../lib/api";
import {
  Wrench,
  Cpu,
  Layers,
  Sparkles,
  CheckCircle,
  Briefcase,
} from "lucide-react";

export interface SkillCategory {
  category: string;
  skills: string[];
}

export interface ProficiencyExpectations {
  trade_id: string;
  trade_name: string;
  district_id: string;
  district_name: string;
  summary: string;
  top_in_demand_skills: string[];
  skill_categories: SkillCategory[];
}

interface TradeOption {
  id: string;
  name: string;
}

export function ProficiencyExpectationsView() {
  const [trades, setTrades] = useState<TradeOption[]>([]);
  const [selectedTradeId, setSelectedTradeId] = useState<string>("");
  const [expectations, setExpectations] = useState<ProficiencyExpectations | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Load available trades from courses first
  useEffect(() => {
    const fetchTrades = async () => {
      try {
        const courses = await api<Array<{ trade_id: string; trade_name: string }>>(
          "/trainee/courses"
        );
        const uniqueTradesMap = new Map<string, string>();
        courses.forEach((c) => uniqueTradesMap.set(c.trade_id, c.trade_name));
        const tradeList = Array.from(uniqueTradesMap.entries()).map(([id, name]) => ({
          id,
          name,
        }));
        setTrades(tradeList);
        if (tradeList.length > 0 && !selectedTradeId && tradeList[0]) {
          setSelectedTradeId(tradeList[0].id);
        }
      } catch (err) {
        console.error("Failed to load trade list", err);
      }
    };
    fetchTrades();
  }, []);

  // Fetch expectations when trade changes
  useEffect(() => {
    if (!selectedTradeId) return;

    const fetchExpectations = async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await api<ProficiencyExpectations>(
          `/trainee/proficiency-expectations?trade_id=${selectedTradeId}`
        );
        setExpectations(data);
      } catch (err: unknown) {
        setError(
          err instanceof Error
            ? err.message
            : "Failed to load proficiency expectations"
        );
      } finally {
        setLoading(false);
      }
    };

    fetchExpectations();
  }, [selectedTradeId]);

  const getCategoryIcon = (index: number) => {
    switch (index) {
      case 0:
        return <Wrench className="h-5 w-5 text-emerald-600" />;
      case 1:
        return <Layers className="h-5 w-5 text-blue-600" />;
      default:
        return <Cpu className="h-5 w-5 text-purple-600" />;
    }
  };

  return (
    <div className="space-y-6">
      {/* Header & Trade Selector */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-xl font-bold tracking-tight text-slate-900 sm:text-2xl">
            Industry Skill Expectations
          </h2>
          <p className="mt-1 text-sm text-slate-500">
            What local employers in your district are actively seeking in hiring postings
          </p>
        </div>

        {trades.length > 0 && (
          <div className="flex items-center gap-2">
            <label className="text-xs font-semibold uppercase tracking-wider text-slate-500">
              Trade:
            </label>
            <select
              value={selectedTradeId}
              onChange={(e) => setSelectedTradeId(e.target.value)}
              className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-800 shadow-sm focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500"
            >
              {trades.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.name}
                </option>
              ))}
            </select>
          </div>
        )}
      </div>

      {error && (
        <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {error}
        </div>
      )}

      {loading && (
        <div className="space-y-4">
          <div className="h-28 animate-pulse rounded-2xl bg-slate-100" />
          <div className="grid gap-4 sm:grid-cols-3">
            <div className="h-56 animate-pulse rounded-xl bg-slate-100" />
            <div className="h-56 animate-pulse rounded-xl bg-slate-100" />
            <div className="h-56 animate-pulse rounded-xl bg-slate-100" />
          </div>
        </div>
      )}

      {!loading && expectations && (
        <div className="space-y-6">
          {/* Summary Banner */}
          <div className="rounded-2xl border border-emerald-100 bg-emerald-50/50 p-6 shadow-sm">
            <div className="flex items-start gap-4">
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-emerald-600 text-white shadow-md shadow-emerald-200">
                <Briefcase className="h-5 w-5" />
              </div>
              <div className="space-y-2">
                <h3 className="text-base font-bold text-slate-900 sm:text-lg">
                  Demand Summary for {expectations.trade_name} ({expectations.district_name})
                </h3>
                <p className="text-sm leading-relaxed text-slate-700">
                  {expectations.summary}
                </p>

                {/* In Demand Chips */}
                <div className="pt-2">
                  <span className="text-xs font-semibold uppercase tracking-wider text-emerald-800">
                    Priority Hiring Keywords:
                  </span>
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    {expectations.top_in_demand_skills.map((skill, i) => (
                      <span
                        key={i}
                        className="inline-flex items-center gap-1 rounded-full border border-emerald-300 bg-white px-2.5 py-0.5 text-xs font-medium text-emerald-800 shadow-2xs"
                      >
                        <Sparkles className="h-3 w-3 text-emerald-600" />
                        {skill}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Categorized Expectations Grid */}
          <div className="grid gap-6 sm:grid-cols-3">
            {expectations.skill_categories.map((cat, idx) => (
              <div
                key={idx}
                className="flex flex-col justify-between rounded-xl border border-slate-200 bg-white p-5 shadow-sm hover:shadow-md transition-shadow"
              >
                <div>
                  <div className="flex items-center gap-2 border-b border-slate-100 pb-3">
                    {getCategoryIcon(idx)}
                    <h4 className="text-sm font-bold tracking-tight text-slate-900">
                      {cat.category}
                    </h4>
                  </div>

                  <ul className="mt-4 space-y-2.5">
                    {cat.skills.map((item, itemIdx) => (
                      <li
                        key={itemIdx}
                        className="flex items-center gap-2 text-xs font-medium text-slate-700"
                      >
                        <CheckCircle className="h-3.5 w-3.5 shrink-0 text-emerald-500" />
                        <span>{item}</span>
                      </li>
                    ))}
                  </ul>
                </div>

                <div className="mt-6 border-t border-slate-100 pt-3 text-center text-xs text-slate-400">
                  Verified by District Pipeline
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
