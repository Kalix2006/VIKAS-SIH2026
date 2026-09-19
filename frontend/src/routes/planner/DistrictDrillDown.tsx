import React, { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  AlertCircle,
  ArrowLeft,
  FileEdit,
  FileSpreadsheet,
  Search,
  TrendingDown,
  TrendingUp,
} from "lucide-react";
import { api } from "../../lib/api";
import { FlagAnnotateModal } from "./FlagAnnotateModal";
import { CapacityPlanExportModal } from "./CapacityPlanExportModal";

export interface DistrictTradeRow {
  trade_id: string;
  trade_name: string;
  nsqf_code: string;
  gap_id: string | null;
  alignment_score: number;
  gap_score: number;
  gap_type: string | null;
  gap_status: string | null;
  trend_direction: "improving" | "stable" | "deteriorating";
  seats_available: number;
  job_posting_volume: number;
  hiring_to_seats_ratio: number;
  flag_count: number;
  latest_annotation_note: string | null;
  latest_override_status: string | null;
}

export interface DistrictDetailData {
  district_id: string;
  district_name: string;
  state: string;
  alignment_health_score: number;
  health_category: "Healthy" | "Moderate Drift" | "Critical Divergence";
  total_seats: number;
  total_postings: number;
  trades: DistrictTradeRow[];
}

export const DistrictDrillDown: React.FC = () => {
  const { districtId } = useParams<{ districtId: string }>();
  const [data, setData] = useState<DistrictDetailData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters & Search
  const [searchQuery, setSearchQuery] = useState("");
  const [filterType, setFilterType] = useState<"all" | "divergent" | "healthy">("all");

  // Modals state
  const [activeAnnotateRow, setActiveAnnotateRow] = useState<DistrictTradeRow | null>(null);
  const [isExportOpen, setIsExportOpen] = useState(false);

  const fetchDistrictData = async () => {
    if (!districtId) return;
    try {
      setLoading(true);
      setError(null);
      const res = await api<DistrictDetailData>(`/planner/districts/${districtId}`);
      setData(res);
    } catch (err: any) {
      setError(err.message || "Failed to load district trade details.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDistrictData();
  }, [districtId]);

  const handleAnnotationSaved = (
    note: string,
    overrideStatus: string | null,
    newGapStatus: string,
  ) => {
    if (!data || !activeAnnotateRow) return;

    // Update row optimistically in table
    const updatedTrades = data.trades.map((t) => {
      if (t.gap_id === activeAnnotateRow.gap_id) {
        return {
          ...t,
          latest_annotation_note: note,
          latest_override_status: overrideStatus,
          gap_status: newGapStatus,
          flag_count: t.flag_count + 1,
        };
      }
      return t;
    });

    setData({
      ...data,
      trades: updatedTrades,
    });
  };

  const filteredTrades = (data?.trades || []).filter((t) => {
    const matchesSearch =
      t.trade_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      t.nsqf_code.toLowerCase().includes(searchQuery.toLowerCase());

    if (!matchesSearch) return false;

    if (filterType === "divergent") {
      return t.gap_score >= 50.0;
    }
    if (filterType === "healthy") {
      return t.gap_score < 50.0;
    }
    return true;
  });

  if (loading) {
    return (
      <div className="flex min-h-[400px] flex-col items-center justify-center gap-3">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-indigo-600 border-t-transparent" />
        <p className="text-sm font-medium text-slate-500">Loading district trade matrix...</p>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="rounded-3xl border border-rose-200 bg-rose-50 p-8 text-center font-sans">
        <AlertCircle className="mx-auto h-8 w-8 text-rose-600" />
        <h3 className="mt-2 text-base font-bold text-rose-900">District Details Error</h3>
        <p className="mt-1 text-sm text-rose-700">{error || "District not found."}</p>
        <Link
          to="/planner"
          className="mt-4 inline-flex items-center gap-2 rounded-xl bg-slate-900 px-4 py-2 text-xs font-semibold text-white hover:bg-slate-800"
        >
          <ArrowLeft className="h-3.5 w-3.5" /> Back to Map
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Top Breadcrumb & Actions */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 pb-4">
        <div>
          <Link
            to="/planner"
            className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-500 hover:text-slate-900 transition-colors mb-2"
          >
            <ArrowLeft className="h-3.5 w-3.5" /> Back to Geographic Heatmap
          </Link>
          <div className="flex flex-wrap items-center gap-3">
            <h1 className="text-2xl font-black tracking-tight text-slate-900" data-testid="district-title">
              {data.district_name} District
            </h1>
            <span
              className={`rounded-full px-2.5 py-0.5 text-xs font-bold uppercase tracking-wider ${
                data.alignment_health_score >= 75
                  ? "bg-emerald-100 text-emerald-800 border border-emerald-300"
                  : data.alignment_health_score >= 50
                  ? "bg-amber-100 text-amber-800 border border-amber-300"
                  : "bg-rose-100 text-rose-800 border border-rose-300"
              }`}
            >
              Health Index: {data.alignment_health_score}/100 ({data.health_category})
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            State of {data.state} • Comprehensive trade-by-trade alignment and capacity analysis
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <button
            onClick={() => setIsExportOpen(true)}
            data-testid="open-export-btn"
            className="flex items-center gap-2 rounded-xl bg-indigo-600 px-4 py-2.5 text-xs font-bold text-white hover:bg-indigo-700 transition-colors shadow-sm"
          >
            <FileSpreadsheet className="h-4 w-4" />
            Export Capacity Plan
          </button>
        </div>
      </div>

      {/* District KPI Summary */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-2xs">
          <span className="text-xs font-bold uppercase tracking-wider text-slate-400 block">
            Total Institutional Seats
          </span>
          <span className="text-2xl font-black text-slate-900 mt-1 block">
            {data.total_seats} seats
          </span>
          <span className="text-[11px] text-slate-400">across local ITIs and training centers</span>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-2xs">
          <span className="text-xs font-bold uppercase tracking-wider text-slate-400 block">
            Active Job Vacancies
          </span>
          <span className="text-2xl font-black text-slate-900 mt-1 block">
            {data.total_postings} postings
          </span>
          <span className="text-[11px] text-slate-400">aggregated from Adzuna & Jooble</span>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-2xs">
          <span className="text-xs font-bold uppercase tracking-wider text-slate-400 block">
            Monitored Vocational Trades
          </span>
          <span className="text-2xl font-black text-indigo-600 mt-1 block">
            {data.trades.length} trades
          </span>
          <span className="text-[11px] text-slate-400">NSQF vocational standards</span>
        </div>
      </div>

      {/* Controls & Filter Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-white p-3 rounded-2xl border border-slate-200 shadow-2xs">
        {/* Search */}
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search trades or NSQF code..."
            className="w-full rounded-xl border border-slate-200 pl-9 pr-3 py-1.5 text-xs focus:border-indigo-500 focus:outline-none shadow-2xs"
          />
        </div>

        {/* Filter Tabs */}
        <div className="flex items-center gap-1 bg-slate-100 p-1 rounded-xl text-xs font-semibold">
          <button
            onClick={() => setFilterType("all")}
            className={`px-3 py-1 rounded-lg transition-colors ${
              filterType === "all" ? "bg-white text-slate-900 shadow-2xs font-bold" : "text-slate-600"
            }`}
          >
            All Trades ({data.trades.length})
          </button>
          <button
            onClick={() => setFilterType("divergent")}
            className={`px-3 py-1 rounded-lg transition-colors ${
              filterType === "divergent"
                ? "bg-white text-rose-800 shadow-2xs font-bold"
                : "text-slate-600"
            }`}
          >
            Drifted / Critical ({data.trades.filter((t) => t.gap_score >= 50).length})
          </button>
          <button
            onClick={() => setFilterType("healthy")}
            className={`px-3 py-1 rounded-lg transition-colors ${
              filterType === "healthy"
                ? "bg-white text-emerald-800 shadow-2xs font-bold"
                : "text-slate-600"
            }`}
          >
            Healthy ({data.trades.filter((t) => t.gap_score < 50).length})
          </button>
        </div>
      </div>

      {/* Trade Data Table */}
      <div className="overflow-x-auto rounded-3xl border border-slate-200 bg-white shadow-sm">
        <table className="w-full text-left text-xs border-collapse" data-testid="drilldown-table">
          <thead className="bg-slate-50/80 text-slate-600 font-bold uppercase tracking-wider border-b border-slate-200">
            <tr>
              <th className="p-4">Vocational Trade</th>
              <th className="p-4 text-center">Alignment Score</th>
              <th className="p-4">Divergence Type</th>
              <th className="p-4 text-center">Trend</th>
              <th className="p-4 text-right">Intake Capacity</th>
              <th className="p-4 text-right">Market Demand</th>
              <th className="p-4 text-center">Ratio</th>
              <th className="p-4">Supervisory Status</th>
              <th className="p-4 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {filteredTrades.map((row) => (
              <tr key={row.trade_id} className="hover:bg-slate-50/60 transition-colors">
                {/* Trade & NSQF */}
                <td className="p-4">
                  <span className="font-bold text-slate-900 text-sm block">
                    {row.trade_name}
                  </span>
                  <span className="text-[11px] text-slate-400 font-mono">
                    NSQF: {row.nsqf_code}
                  </span>
                </td>

                {/* Alignment Score Gauge */}
                <td className="p-4 text-center">
                  <div className="inline-flex flex-col items-center">
                    <span
                      className={`text-sm font-black ${
                        row.alignment_score >= 75
                          ? "text-emerald-700"
                          : row.alignment_score >= 50
                          ? "text-amber-700"
                          : "text-rose-700"
                      }`}
                    >
                      {row.alignment_score}
                    </span>
                    <span className="text-[10px] text-slate-400">/ 100</span>
                  </div>
                </td>

                {/* Gap Type */}
                <td className="p-4">
                  {row.gap_type ? (
                    <span
                      className={`rounded-full px-2.5 py-0.5 text-[11px] font-bold capitalize ${
                        row.gap_type === "curriculum_drift"
                          ? "bg-rose-100 text-rose-900"
                          : row.gap_type === "oversupply"
                          ? "bg-amber-100 text-amber-900"
                          : "bg-blue-100 text-blue-900"
                      }`}
                    >
                      {row.gap_type.replace("_", " ")}
                    </span>
                  ) : (
                    <span className="text-slate-400 text-[11px] italic">No drift detected</span>
                  )}
                </td>

                {/* Trend Direction */}
                <td className="p-4 text-center">
                  <span
                    className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider ${
                      row.trend_direction === "improving"
                        ? "bg-emerald-50 text-emerald-700"
                        : row.trend_direction === "stable"
                        ? "bg-slate-100 text-slate-600"
                        : "bg-rose-50 text-rose-700"
                    }`}
                  >
                    {row.trend_direction === "improving" && <TrendingUp className="h-3 w-3 text-emerald-600" />}
                    {row.trend_direction === "deteriorating" && <TrendingDown className="h-3 w-3 text-rose-600" />}
                    {row.trend_direction}
                  </span>
                </td>

                {/* Seats Available */}
                <td className="p-4 text-right">
                  <span className="font-bold text-slate-800">{row.seats_available}</span>
                  <span className="text-[10px] text-slate-400 block">seats</span>
                </td>

                {/* Job Posting Volume */}
                <td className="p-4 text-right">
                  <span className="font-bold text-slate-800">{row.job_posting_volume}</span>
                  <span className="text-[10px] text-slate-400 block">vacancies</span>
                </td>

                {/* Hiring to Seats Ratio */}
                <td className="p-4 text-center">
                  <span
                    className={`rounded-full px-2 py-0.5 text-xs font-black ${
                      row.hiring_to_seats_ratio >= 1.5
                        ? "bg-emerald-100 text-emerald-800"
                        : row.hiring_to_seats_ratio <= 0.5
                        ? "bg-rose-100 text-rose-800"
                        : "bg-slate-100 text-slate-700"
                    }`}
                  >
                    {row.hiring_to_seats_ratio}x
                  </span>
                </td>

                {/* Supervisory Status & Latest Note */}
                <td className="p-4 max-w-xs">
                  {row.latest_override_status ? (
                    <div className="space-y-1">
                      <span
                        className={`rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider ${
                          row.latest_override_status === "confirmed"
                            ? "bg-amber-100 text-amber-900 border border-amber-300"
                            : "bg-rose-100 text-rose-900 border border-rose-300"
                        }`}
                      >
                        Override: {row.latest_override_status}
                      </span>
                      {row.latest_annotation_note && (
                        <p className="text-[11px] text-slate-600 line-clamp-1 italic">
                          "{row.latest_annotation_note}"
                        </p>
                      )}
                    </div>
                  ) : row.latest_annotation_note ? (
                    <p className="text-[11px] text-slate-600 line-clamp-1 italic">
                      "{row.latest_annotation_note}"
                    </p>
                  ) : (
                    <span className="text-slate-400 text-[11px]">Unannotated</span>
                  )}
                </td>

                {/* Actions */}
                <td className="p-4 text-right">
                  <div className="flex items-center justify-end gap-1.5">
                    {/* Compare Button */}
                    <Link
                      to={`/planner/compare?district_ids=${data.district_id}&trade_id=${row.trade_id}`}
                      className="rounded-lg border border-slate-200 bg-white px-2.5 py-1 text-[11px] font-semibold text-slate-700 hover:bg-slate-50 transition-colors shadow-2xs"
                      title="Compare this trade with another district"
                    >
                      Compare
                    </Link>

                    {/* Annotate Button */}
                    <button
                      type="button"
                      disabled={!row.gap_id}
                      onClick={() => setActiveAnnotateRow(row)}
                      data-testid={`annotate-btn-${row.trade_id}`}
                      className="flex items-center gap-1 rounded-lg bg-amber-500 px-2.5 py-1 text-[11px] font-bold text-white hover:bg-amber-600 transition-colors shadow-2xs disabled:opacity-30 disabled:cursor-not-allowed"
                      title="Add planner note or override flag"
                    >
                      <FileEdit className="h-3 w-3" />
                      Annotate
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Flag Annotation Modal */}
      {activeAnnotateRow && (
        <FlagAnnotateModal
          isOpen={!!activeAnnotateRow}
          onClose={() => setActiveAnnotateRow(null)}
          tradeName={activeAnnotateRow.trade_name}
          districtName={data.district_name}
          gapId={activeAnnotateRow.gap_id}
          initialNote={activeAnnotateRow.latest_annotation_note}
          initialOverrideStatus={activeAnnotateRow.latest_override_status}
          onAnnotationSaved={handleAnnotationSaved}
        />
      )}

      {/* Capacity Plan Export Modal */}
      {isExportOpen && (
        <CapacityPlanExportModal
          isOpen={isExportOpen}
          onClose={() => setIsExportOpen(false)}
          districtId={data.district_id}
          districtName={data.district_name}
        />
      )}
    </div>
  );
};
export default DistrictDrillDown;
