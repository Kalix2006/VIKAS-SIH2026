import { useState, useEffect } from "react";
import { ShieldCheck, Users, GraduationCap, Award, RefreshCw, AlertCircle } from "lucide-react";
import { api } from "../../lib/api";
import { useAuth } from "../../lib/auth";

interface CompetencyMastery {
  competency_name: string;
  category: string;
  mastery_percentage: number;
}

interface ReadinessDistribution {
  high_readiness: number;
  moderate_readiness: number;
  foundational: number;
}

interface AggregateReadinessResponse {
  trade_id: string;
  trade_name: string;
  nsqf_code: string;
  district_id: string;
  district_name: string;
  total_enrolled_trainees: number;
  graduating_within_90_days: number;
  cohort_readiness_index: number;
  readiness_distribution: ReadinessDistribution;
  competency_mastery: CompetencyMastery[];
  contributing_institutes_count: number;
  privacy_guarantee: string;
}

interface TradeOption {
  id: string;
  name: string;
  nsqf_code: string;
}

export function AggregateReadinessView() {
  const { user } = useAuth();
  const [trades, setTrades] = useState<TradeOption[]>([]);
  const [selectedTradeId, setSelectedTradeId] = useState<string>("");
  const [readiness, setReadiness] = useState<AggregateReadinessResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadTrades() {
      try {
        const res = await api<any[]>("/trainee/courses?district_id=" + (user?.district_id || ""));
        if (Array.isArray(res)) {
          const uniqueTrades = Array.from(
            new Map(res.map((c) => [c.trade_id, { id: c.trade_id, name: c.trade_name, nsqf_code: c.nsqf_code }])).values()
          );
          setTrades(uniqueTrades as TradeOption[]);
          if (uniqueTrades.length > 0 && uniqueTrades[0]) {
            setSelectedTradeId((uniqueTrades[0] as TradeOption).id);
          }
        }
      } catch {
        const fallbackTrades: TradeOption[] = [
          { id: "e1000000-0000-0000-0000-000000000001", name: "Electrician", nsqf_code: "NSQF-L4-ELE" },
          { id: "f2000000-0000-0000-0000-000000000002", name: "Fitter", nsqf_code: "NSQF-L4-FIT" },
          { id: "w3000000-0000-0000-0000-000000000003", name: "Welder", nsqf_code: "NSQF-L4-WLD" },
          { id: "a4000000-0000-0000-0000-000000000004", name: "Automobile/Diesel Mechanic", nsqf_code: "MEC/Q0101" },
          { id: "c5000000-0000-0000-0000-000000000005", name: "COPA", nsqf_code: "NSQF-L4-COP" },
        ];
        setTrades(fallbackTrades);
        if (fallbackTrades[0]) {
          setSelectedTradeId(fallbackTrades[0].id);
        }
      }
    }
    loadTrades();
  }, [user?.district_id]);

  useEffect(() => {
    if (!selectedTradeId || !user?.district_id) return;
    async function fetchReadiness() {
      setLoading(true);
      setError(null);
      try {
        const data = await api<AggregateReadinessResponse>(
          `/employer/aggregate-readiness?trade_id=${selectedTradeId}&district_id=${user?.district_id}`
        );
        setReadiness(data);
      } catch (err: any) {
        setError(err.message || "Failed to load cohort readiness");
      } finally {
        setLoading(false);
      }
    }
    fetchReadiness();
  }, [selectedTradeId, user?.district_id]);

  return (
    <div className="space-y-6">
      {/* Privacy Guarantee Banner */}
      <div
        data-testid="privacy-banner"
        className="rounded-xl border border-emerald-200 bg-emerald-50/70 p-4 shadow-sm flex items-start gap-3"
      >
        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-emerald-600 text-white shrink-0 mt-0.5">
          <ShieldCheck className="h-5 w-5" />
        </div>
        <div>
          <h3 className="text-xs font-bold uppercase tracking-wider text-emerald-900">
            Privacy-by-Design Governance Guarantee
          </h3>
          <p className="text-xs text-emerald-800 mt-0.5">
            Statistical district-level aggregate across accredited ITIs and PMKVY training centers. In strict compliance with Indian Data Protection principles, this role accesses statistical cohorts only — zero candidate PII or individual trainee identifiers are ever surfaced.
          </p>
        </div>
      </div>

      {/* Trade Selector */}
      <div className="flex flex-wrap items-center justify-between gap-4 bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
        <div className="flex items-center gap-3">
          <label className="text-xs font-bold uppercase tracking-wider text-slate-600">
            Inspect Cohort Trade:
          </label>
          <select
            value={selectedTradeId}
            onChange={(e) => setSelectedTradeId(e.target.value)}
            className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm font-semibold text-slate-800 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          >
            {trades.map((t) => (
              <option key={t.id} value={t.id}>
                {t.name} ({t.nsqf_code})
              </option>
            ))}
          </select>
        </div>

        {readiness && (
          <div className="text-xs text-slate-500">
            District: <span className="font-semibold text-slate-700">{readiness.district_name}</span> ({readiness.contributing_institutes_count} training centers)
          </div>
        )}
      </div>

      {error && (
        <div className="flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
          <AlertCircle className="h-4 w-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {loading ? (
        <div className="flex h-48 items-center justify-center rounded-xl border border-slate-200 bg-white">
          <div className="flex items-center gap-2 text-sm text-slate-500">
            <RefreshCw className="h-4 w-4 animate-spin text-blue-600" />
            Aggregating district cohort readiness metrics...
          </div>
        </div>
      ) : readiness ? (
        <div className="space-y-6">
          {/* Key Metric KPI Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
              <div className="flex items-center justify-between text-slate-500 mb-2">
                <span className="text-xs font-bold uppercase tracking-wider">Total Enrolled Cohort</span>
                <Users className="h-4 w-4 text-blue-600" />
              </div>
              <div className="text-2xl font-black text-slate-900" data-testid="stat-enrolled">
                {readiness.total_enrolled_trainees}
              </div>
              <div className="text-[11px] text-slate-500 mt-1">
                Active students across district ITIs
              </div>
            </div>

            <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
              <div className="flex items-center justify-between text-slate-500 mb-2">
                <span className="text-xs font-bold uppercase tracking-wider">Graduating Near-Term</span>
                <GraduationCap className="h-4 w-4 text-emerald-600" />
              </div>
              <div className="text-2xl font-black text-emerald-600" data-testid="stat-graduating">
                {readiness.graduating_within_90_days}
              </div>
              <div className="text-[11px] text-slate-500 mt-1">
                Available for placement within 90 days
              </div>
            </div>

            <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
              <div className="flex items-center justify-between text-slate-500 mb-2">
                <span className="text-xs font-bold uppercase tracking-wider">Cohort Readiness Index</span>
                <Award className="h-4 w-4 text-purple-600" />
              </div>
              <div className="text-2xl font-black text-purple-700" data-testid="stat-readiness-index">
                {readiness.cohort_readiness_index}%
              </div>
              <div className="text-[11px] text-slate-500 mt-1">
                Weighted curricular & practical benchmark
              </div>
            </div>
          </div>

          {/* Readiness Distribution Tiers */}
          <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm space-y-3">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-700">
              Statistical Readiness Distribution
            </h3>
            <div className="grid grid-cols-3 gap-3 pt-1">
              <div className="rounded-lg border border-emerald-200 bg-emerald-50/50 p-3 text-center">
                <div className="text-lg font-bold text-emerald-700">
                  {readiness.readiness_distribution.high_readiness}
                </div>
                <div className="text-xs font-semibold text-emerald-900 mt-0.5">High Readiness</div>
                <div className="text-[10px] text-emerald-600">Immediate placement ready (≥80%)</div>
              </div>

              <div className="rounded-lg border border-blue-200 bg-blue-50/50 p-3 text-center">
                <div className="text-lg font-bold text-blue-700">
                  {readiness.readiness_distribution.moderate_readiness}
                </div>
                <div className="text-xs font-semibold text-blue-900 mt-0.5">Moderate Readiness</div>
                <div className="text-[10px] text-blue-600">Final module completion (50-79%)</div>
              </div>

              <div className="rounded-lg border border-slate-200 bg-slate-50 p-3 text-center">
                <div className="text-lg font-bold text-slate-700">
                  {readiness.readiness_distribution.foundational}
                </div>
                <div className="text-xs font-semibold text-slate-800 mt-0.5">Foundational</div>
                <div className="text-[10px] text-slate-500">First semester / core skills (&lt;50%)</div>
              </div>
            </div>
          </div>

          {/* Competency Mastery Bars */}
          <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm space-y-4">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-700">
              Aggregated Competency Mastery ({readiness.trade_name})
            </h3>
            <div className="space-y-3">
              {readiness.competency_mastery.map((comp) => (
                <div key={comp.competency_name} className="space-y-1">
                  <div className="flex items-center justify-between text-xs">
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-slate-800">{comp.competency_name}</span>
                      <span className="rounded bg-slate-100 px-1.5 py-0.5 text-[10px] font-medium text-slate-600">
                        {comp.category}
                      </span>
                    </div>
                    <span className="font-bold text-slate-900">{comp.mastery_percentage}%</span>
                  </div>
                  <div className="h-2 w-full rounded-full bg-slate-100 overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all duration-500 ${
                        comp.mastery_percentage >= 80
                          ? "bg-emerald-500"
                          : comp.mastery_percentage >= 60
                          ? "bg-blue-500"
                          : "bg-amber-500"
                      }`}
                      style={{ width: `${comp.mastery_percentage}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
