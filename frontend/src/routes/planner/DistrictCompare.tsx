import React, { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import {
  AlertCircle,
  ArrowLeft,
  ArrowLeftRight,
  Sparkles,
} from "lucide-react";
import { api } from "../../lib/api";

interface DistrictOption {
  id: string;
  name: string;
  state: string;
}

interface TradeOption {
  id: string;
  name: string;
  nsqf_code: string;
}

interface DistrictComparisonItem {
  district_id: string;
  district_name: string;
  state: string;
  alignment_score: number;
  gap_score: number;
  gap_type: string | null;
  seats_available: number;
  job_posting_volume: number;
  hiring_to_seats_ratio: number;
  top_in_demand_skills: string[];
  gap_status: string | null;
}

interface PlannerCompareResponse {
  trade_id: string;
  trade_name: string;
  nsqf_code: string;
  district_a: DistrictComparisonItem;
  district_b: DistrictComparisonItem;
  alignment_score_delta: number;
  comparative_insight: string;
}

export const DistrictCompare: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();

  // Selector state
  const [districts, setDistricts] = useState<DistrictOption[]>([]);
  const [trades, setTrades] = useState<TradeOption[]>([]);
  const [selectedTradeId, setSelectedTradeId] = useState<string>("");
  const [selectedDistrictA, setSelectedDistrictA] = useState<string>("");
  const [selectedDistrictB, setSelectedDistrictB] = useState<string>("");

  // Comparison data state
  const [compareData, setCompareData] = useState<PlannerCompareResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [initialLoading, setInitialLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // 1. Initial load of district and trade options
  useEffect(() => {
    const fetchOptions = async () => {
      try {
        setInitialLoading(true);
        const mapRes = await api<{ districts: DistrictOption[] }>("/planner/map");
        setDistricts(mapRes.districts);

        // If districts exist, load trade options from first district's drill-down
        if (mapRes.districts && mapRes.districts.length > 0) {
          const firstDist = mapRes.districts[0];
          if (firstDist) {
            const distDetail = await api<{
              trades: { trade_id: string; trade_name: string; nsqf_code: string }[];
            }>(`/planner/districts/${firstDist.id}`);
            const tradeOpts = distDetail.trades.map((t) => ({
              id: t.trade_id,
              name: t.trade_name,
              nsqf_code: t.nsqf_code,
            }));
            setTrades(tradeOpts);

            // Initialize from search params or defaults
            const paramDistIds = searchParams.get("district_ids")?.split(",") || [];
            const paramTradeId = searchParams.get("trade_id");

            const distA = paramDistIds[0] || firstDist.id || "";
            const distB =
              paramDistIds[1] ||
              (mapRes.districts.length > 1 && mapRes.districts[1] ? mapRes.districts[1].id : distA);
            const trId = paramTradeId || (tradeOpts.length > 0 && tradeOpts[0] ? tradeOpts[0].id : "");

            setSelectedDistrictA(distA);
            setSelectedDistrictB(distB);
            setSelectedTradeId(trId);
          }
        }
      } catch (err: any) {
        setError(err.message || "Failed to load comparison options.");
      } finally {
        setInitialLoading(false);
      }
    };

    fetchOptions();
  }, []);

  // 2. Fetch comparison when selections change
  const executeComparison = async (distA: string, distB: string, tradeId: string) => {
    if (!distA || !distB || !tradeId) return;
    try {
      setLoading(true);
      setError(null);
      const res = await api<PlannerCompareResponse>(
        `/planner/compare?district_ids=${distA},${distB}&trade_id=${tradeId}`,
      );
      setCompareData(res);
      // Update URL search params
      setSearchParams({
        district_ids: `${distA},${distB}`,
        trade_id: tradeId,
      });
    } catch (err: any) {
      setError(err.message || "Failed to generate comparison.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (selectedDistrictA && selectedDistrictB && selectedTradeId) {
      executeComparison(selectedDistrictA, selectedDistrictB, selectedTradeId);
    }
  }, [selectedDistrictA, selectedDistrictB, selectedTradeId]);

  if (initialLoading) {
    return (
      <div className="flex min-h-[400px] flex-col items-center justify-center gap-3 font-sans">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-indigo-600 border-t-transparent" />
        <p className="text-sm font-medium text-slate-500">Loading cross-district benchmarking...</p>
      </div>
    );
  }

  return (
    <div className="space-y-6 font-sans">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 pb-4">
        <div>
          <Link
            to="/planner"
            className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-500 hover:text-slate-900 transition-colors mb-2"
          >
            <ArrowLeft className="h-3.5 w-3.5" /> Back to Map
          </Link>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-black tracking-tight text-slate-900">
              Cross-District Trade Benchmarking
            </h1>
            <span className="inline-flex items-center gap-1 rounded-full bg-indigo-50 px-2.5 py-0.5 text-xs font-bold text-indigo-700 border border-indigo-200">
              <ArrowLeftRight className="h-3.5 w-3.5" /> Side-by-Side Analysis
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Compare syllabus alignment, vacancy pressures, and specific demanded skills between two districts for any trade.
          </p>
        </div>
      </div>

      {/* Selectors Card */}
      <div className="rounded-3xl border border-slate-200 bg-white p-5 shadow-2xs space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Trade Selector */}
          <div>
            <label className="block text-xs font-bold uppercase tracking-wider text-slate-600 mb-1.5">
              Select Vocational Trade
            </label>
            <select
              value={selectedTradeId}
              onChange={(e) => setSelectedTradeId(e.target.value)}
              className="w-full rounded-xl border border-slate-200 bg-slate-50/70 p-2.5 text-xs font-semibold text-slate-800 focus:border-indigo-500 focus:outline-none"
            >
              {trades.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.name} ({t.nsqf_code})
                </option>
              ))}
            </select>
          </div>

          {/* District A Selector */}
          <div>
            <label className="block text-xs font-bold uppercase tracking-wider text-slate-600 mb-1.5">
              District A (Primary)
            </label>
            <select
              value={selectedDistrictA}
              onChange={(e) => setSelectedDistrictA(e.target.value)}
              className="w-full rounded-xl border border-slate-200 bg-slate-50/70 p-2.5 text-xs font-semibold text-slate-800 focus:border-indigo-500 focus:outline-none"
            >
              {districts.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.name} ({d.state})
                </option>
              ))}
            </select>
          </div>

          {/* District B Selector */}
          <div>
            <label className="block text-xs font-bold uppercase tracking-wider text-slate-600 mb-1.5">
              District B (Comparison)
            </label>
            <select
              value={selectedDistrictB}
              onChange={(e) => setSelectedDistrictB(e.target.value)}
              className="w-full rounded-xl border border-slate-200 bg-slate-50/70 p-2.5 text-xs font-semibold text-slate-800 focus:border-indigo-500 focus:outline-none"
            >
              {districts.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.name} ({d.state})
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {loading && (
        <div className="flex min-h-[300px] flex-col items-center justify-center gap-3">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-indigo-600 border-t-transparent" />
          <p className="text-sm font-medium text-slate-500">Benchmarking trade metrics...</p>
        </div>
      )}

      {error && (
        <div className="rounded-2xl border border-rose-200 bg-rose-50 p-6 text-center">
          <AlertCircle className="mx-auto h-8 w-8 text-rose-500" />
          <p className="mt-2 text-sm font-semibold text-rose-800">{error}</p>
        </div>
      )}

      {/* Comparative Results View */}
      {!loading && !error && compareData && (
        <div className="space-y-6" data-testid="compare-results">
          {/* Delta & Strategic Insight Banner */}
          <div className="rounded-3xl border border-indigo-200 bg-indigo-50/70 p-5 shadow-2xs flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <Sparkles className="h-4 w-4 text-indigo-600" />
                <span className="text-xs font-bold uppercase tracking-wider text-indigo-900">
                  Strategic Comparative Insight
                </span>
              </div>
              <p className="text-sm font-medium text-indigo-950 leading-relaxed max-w-3xl">
                {compareData.comparative_insight}
              </p>
            </div>

            <div className="shrink-0 bg-white rounded-2xl border border-indigo-200/80 px-4 py-3 text-right shadow-2xs">
              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block">
                Alignment Delta (A - B)
              </span>
              <span
                className={`text-2xl font-black block ${
                  compareData.alignment_score_delta > 0
                    ? "text-emerald-600"
                    : compareData.alignment_score_delta < 0
                    ? "text-rose-600"
                    : "text-slate-700"
                }`}
              >
                {compareData.alignment_score_delta > 0 ? "+" : ""}
                {compareData.alignment_score_delta} pts
              </span>
            </div>
          </div>

          {/* Side-by-Side Columns */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* District A Card */}
            <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm space-y-5">
              <div className="flex items-start justify-between border-b border-slate-100 pb-4">
                <div>
                  <span className="text-[10px] font-bold uppercase tracking-wider text-indigo-600 bg-indigo-50 px-2.5 py-0.5 rounded-full border border-indigo-100">
                    District A (Primary)
                  </span>
                  <h3 className="text-xl font-black text-slate-900 mt-1">
                    {compareData.district_a.district_name}
                  </h3>
                  <span className="text-xs text-slate-400">{compareData.district_a.state}</span>
                </div>

                <div className="text-right">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block">
                    Alignment Score
                  </span>
                  <span
                    className={`text-3xl font-black ${
                      compareData.district_a.alignment_score >= 75
                        ? "text-emerald-700"
                        : compareData.district_a.alignment_score >= 50
                        ? "text-amber-700"
                        : "text-rose-700"
                    }`}
                  >
                    {compareData.district_a.alignment_score}
                  </span>
                  <span className="text-xs text-slate-400">/ 100</span>
                </div>
              </div>

              {/* Metrics Grid */}
              <div className="grid grid-cols-3 gap-3 bg-slate-50/70 p-3.5 rounded-2xl">
                <div>
                  <span className="text-[10px] font-bold uppercase text-slate-400 block">
                    Seats Available
                  </span>
                  <span className="text-base font-bold text-slate-800">
                    {compareData.district_a.seats_available}
                  </span>
                </div>
                <div>
                  <span className="text-[10px] font-bold uppercase text-slate-400 block">
                    Job Vacancies
                  </span>
                  <span className="text-base font-bold text-slate-800">
                    {compareData.district_a.job_posting_volume}
                  </span>
                </div>
                <div>
                  <span className="text-[10px] font-bold uppercase text-slate-400 block">
                    Hiring Ratio
                  </span>
                  <span className="text-base font-black text-indigo-600">
                    {compareData.district_a.hiring_to_seats_ratio}x
                  </span>
                </div>
              </div>

              {/* In-Demand Skills */}
              <div className="space-y-2">
                <span className="text-xs font-bold uppercase tracking-wider text-slate-700 block">
                  Top Skills Demanded in {compareData.district_a.district_name} Vacancies
                </span>
                <div className="flex flex-wrap gap-1.5">
                  {compareData.district_a.top_in_demand_skills.map((skill, idx) => (
                    <span
                      key={idx}
                      className="rounded-xl border border-slate-200 bg-white px-2.5 py-1 text-xs font-semibold text-slate-700 shadow-2xs"
                    >
                      {skill}
                    </span>
                  ))}
                </div>
              </div>
            </div>

            {/* District B Card */}
            <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm space-y-5">
              <div className="flex items-start justify-between border-b border-slate-100 pb-4">
                <div>
                  <span className="text-[10px] font-bold uppercase tracking-wider text-slate-600 bg-slate-100 px-2.5 py-0.5 rounded-full border border-slate-200">
                    District B (Benchmark)
                  </span>
                  <h3 className="text-xl font-black text-slate-900 mt-1">
                    {compareData.district_b.district_name}
                  </h3>
                  <span className="text-xs text-slate-400">{compareData.district_b.state}</span>
                </div>

                <div className="text-right">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block">
                    Alignment Score
                  </span>
                  <span
                    className={`text-3xl font-black ${
                      compareData.district_b.alignment_score >= 75
                        ? "text-emerald-700"
                        : compareData.district_b.alignment_score >= 50
                        ? "text-amber-700"
                        : "text-rose-700"
                    }`}
                  >
                    {compareData.district_b.alignment_score}
                  </span>
                  <span className="text-xs text-slate-400">/ 100</span>
                </div>
              </div>

              {/* Metrics Grid */}
              <div className="grid grid-cols-3 gap-3 bg-slate-50/70 p-3.5 rounded-2xl">
                <div>
                  <span className="text-[10px] font-bold uppercase text-slate-400 block">
                    Seats Available
                  </span>
                  <span className="text-base font-bold text-slate-800">
                    {compareData.district_b.seats_available}
                  </span>
                </div>
                <div>
                  <span className="text-[10px] font-bold uppercase text-slate-400 block">
                    Job Vacancies
                  </span>
                  <span className="text-base font-bold text-slate-800">
                    {compareData.district_b.job_posting_volume}
                  </span>
                </div>
                <div>
                  <span className="text-[10px] font-bold uppercase text-slate-400 block">
                    Hiring Ratio
                  </span>
                  <span className="text-base font-black text-indigo-600">
                    {compareData.district_b.hiring_to_seats_ratio}x
                  </span>
                </div>
              </div>

              {/* In-Demand Skills */}
              <div className="space-y-2">
                <span className="text-xs font-bold uppercase tracking-wider text-slate-700 block">
                  Top Skills Demanded in {compareData.district_b.district_name} Vacancies
                </span>
                <div className="flex flex-wrap gap-1.5">
                  {compareData.district_b.top_in_demand_skills.map((skill, idx) => (
                    <span
                      key={idx}
                      className="rounded-xl border border-slate-200 bg-white px-2.5 py-1 text-xs font-semibold text-slate-700 shadow-2xs"
                    >
                      {skill}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
export default DistrictCompare;
