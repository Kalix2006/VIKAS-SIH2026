import React, { useEffect, useState } from "react";
import {
  AlertCircle,
  CheckCircle2,
  Download,
  FileSpreadsheet,
  Printer,
  TrendingDown,
  TrendingUp,
  Users,
  Wrench,
  X,
} from "lucide-react";
import { api, API_BASE_URL } from "../../lib/api";

interface CapacityPlanRecommendation {
  trade_id: string;
  trade_name: string;
  nsqf_code: string;
  current_seats: number;
  active_vacancies: number;
  recommended_seat_adjustment: number;
  recommended_trainer_workshops: number;
  equipment_investment_priority: "High" | "Medium" | "Low";
  investment_focus: string;
  rationale: string;
}

interface CapacityPlanData {
  district_id: string;
  district_name: string;
  state: string;
  generated_at: string;
  total_recommended_seat_change: number;
  total_trainer_workshops: number;
  recommendations: CapacityPlanRecommendation[];
}

interface CapacityPlanExportModalProps {
  isOpen: boolean;
  onClose: () => void;
  districtId: string;
  districtName: string;
}

export const CapacityPlanExportModal: React.FC<CapacityPlanExportModalProps> = ({
  isOpen,
  onClose,
  districtId,
  districtName,
}) => {
  const [data, setData] = useState<CapacityPlanData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [downloadSuccess, setDownloadSuccess] = useState<string | null>(null);

  useEffect(() => {
    if (!isOpen || !districtId) return;

    const fetchPlan = async () => {
      try {
        setLoading(true);
        setError(null);
        setDownloadSuccess(null);
        const res = await api<CapacityPlanData>(
          `/planner/export/capacity-plan?district_id=${districtId}&format=json`,
        );
        setData(res);
      } catch (err: any) {
        setError(err.message || "Failed to load capacity recommendations.");
      } finally {
        setLoading(false);
      }
    };

    fetchPlan();
  }, [isOpen, districtId]);

  if (!isOpen) return null;

  const handleDownloadJSON = () => {
    if (!data) return;
    const jsonStr = JSON.stringify(data, null, 2);
    const blob = new Blob([jsonStr], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `capacity_plan_${districtName.toLowerCase().replace(/\s+/g, "_")}.json`;
    a.click();
    URL.revokeObjectURL(url);
    setDownloadSuccess("JSON Capacity Plan downloaded successfully!");
  };

  const handleDownloadCSV = async () => {
    try {
      setDownloadSuccess(null);
      const token = localStorage.getItem("access_token");
      const res = await fetch(
        `${API_BASE_URL}/planner/export/capacity-plan?district_id=${districtId}&format=csv`,
        {
          headers: token ? { Authorization: `Bearer ${token}` } : {},
        },
      );
      if (!res.ok) throw new Error("Failed to download CSV");
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `capacity_plan_${districtName.toLowerCase().replace(/\s+/g, "_")}.csv`;
      a.click();
      URL.revokeObjectURL(url);
      setDownloadSuccess("CSV Capacity Plan downloaded successfully!");
    } catch {
      // Fallback client-side CSV generation if direct endpoint download hit CORS
      if (!data) return;
      const headers = [
        "District",
        "State",
        "Trade Name",
        "NSQF Code",
        "Current Seats",
        "Active Vacancies",
        "Seat Adjustment",
        "Trainer Workshops",
        "Equipment Priority",
        "Investment Focus",
        "Rationale",
      ];
      const rows = data.recommendations.map((r) => [
        `"${data.district_name}"`,
        `"${data.state}"`,
        `"${r.trade_name}"`,
        `"${r.nsqf_code}"`,
        r.current_seats,
        r.active_vacancies,
        r.recommended_seat_adjustment,
        r.recommended_trainer_workshops,
        `"${r.equipment_investment_priority}"`,
        `"${r.investment_focus.replace(/"/g, '""')}"`,
        `"${r.rationale.replace(/"/g, '""')}"`,
      ]);
      const csvContent = [headers.join(","), ...rows.map((row) => row.join(","))].join("\n");
      const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `capacity_plan_${districtName.toLowerCase().replace(/\s+/g, "_")}.csv`;
      a.click();
      URL.revokeObjectURL(url);
      setDownloadSuccess("CSV Capacity Plan downloaded successfully!");
    }
  };

  const handlePrintReport = () => {
    window.print();
  };

  const highPriorityCount =
    data?.recommendations.filter((r) => r.equipment_investment_priority === "High")
      .length || 0;

  return (
    <div
      data-testid="capacity-export-modal"
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-xs p-4 font-sans"
    >
      <div className="w-full max-w-4xl max-h-[90vh] flex flex-col rounded-3xl border border-slate-200 bg-white shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-150">
        {/* Header */}
        <div className="flex items-start justify-between border-b border-slate-100 p-6 pb-4 shrink-0">
          <div>
            <div className="flex items-center gap-2">
              <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-indigo-50 text-indigo-700 border border-indigo-200">
                <FileSpreadsheet className="h-4 w-4" />
              </div>
              <h3 className="text-xl font-black tracking-tight text-slate-900">
                Strategic Capacity Plan Export
              </h3>
            </div>
            <p className="text-xs text-slate-500 mt-1">
              Automated institutional resource planning for{" "}
              <strong className="text-slate-800">{districtName} District</strong> based on local employer demand.
            </p>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-600 transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Content Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {loading && (
            <div className="flex min-h-[250px] flex-col items-center justify-center gap-3">
              <div className="h-8 w-8 animate-spin rounded-full border-4 border-indigo-600 border-t-transparent" />
              <p className="text-sm font-medium text-slate-500">
                Generating capacity recommendations...
              </p>
            </div>
          )}

          {error && (
            <div className="rounded-2xl border border-rose-200 bg-rose-50 p-4 text-xs font-semibold text-rose-800 flex items-center gap-2">
              <AlertCircle className="h-4 w-4 shrink-0 text-rose-600" />
              {error}
            </div>
          )}

          {downloadSuccess && (
            <div className="rounded-2xl border border-emerald-200 bg-emerald-50 p-3 text-xs font-semibold text-emerald-800 flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-600" />
              {downloadSuccess}
            </div>
          )}

          {data && (
            <>
              {/* Executive Summary Metrics */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div className="rounded-2xl border border-slate-200 bg-slate-50/70 p-4">
                  <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500 block">
                    Net Seat Shift
                  </span>
                  <div className="flex items-center gap-2 mt-1">
                    {data.total_recommended_seat_change >= 0 ? (
                      <TrendingUp className="h-5 w-5 text-emerald-600" />
                    ) : (
                      <TrendingDown className="h-5 w-5 text-rose-600" />
                    )}
                    <span className="text-2xl font-black text-slate-900">
                      {data.total_recommended_seat_change >= 0 ? "+" : ""}
                      {data.total_recommended_seat_change}
                    </span>
                    <span className="text-xs text-slate-400 font-medium">seats</span>
                  </div>
                </div>

                <div className="rounded-2xl border border-slate-200 bg-slate-50/70 p-4">
                  <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500 block">
                    Trainer Refresher Workshops
                  </span>
                  <div className="flex items-center gap-2 mt-1">
                    <Users className="h-5 w-5 text-indigo-600" />
                    <span className="text-2xl font-black text-slate-900">
                      {data.total_trainer_workshops}
                    </span>
                    <span className="text-xs text-slate-400 font-medium">sessions</span>
                  </div>
                </div>

                <div className="rounded-2xl border border-slate-200 bg-slate-50/70 p-4">
                  <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500 block">
                    High Priority Capex Needs
                  </span>
                  <div className="flex items-center gap-2 mt-1">
                    <Wrench className="h-5 w-5 text-amber-600" />
                    <span className="text-2xl font-black text-slate-900">
                      {highPriorityCount}
                    </span>
                    <span className="text-xs text-slate-400 font-medium">trades</span>
                  </div>
                </div>
              </div>

              {/* Recommendations Table */}
              <div className="overflow-x-auto rounded-2xl border border-slate-200 shadow-2xs">
                <table className="w-full text-left text-xs border-collapse">
                  <thead className="bg-slate-50 text-slate-700 font-bold uppercase tracking-wider border-b border-slate-200">
                    <tr>
                      <th className="p-3">Trade</th>
                      <th className="p-3 text-right">Current / Demand</th>
                      <th className="p-3 text-center">Seat Adj.</th>
                      <th className="p-3 text-center">Workshops</th>
                      <th className="p-3">Tooling Capex Priority</th>
                      <th className="p-3">Planning Justification</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 bg-white">
                    {data.recommendations.map((rec) => (
                      <tr key={rec.trade_id} className="hover:bg-slate-50/60 transition-colors">
                        <td className="p-3">
                          <span className="font-bold text-slate-900 block">{rec.trade_name}</span>
                          <span className="text-[10px] text-slate-400 font-mono">{rec.nsqf_code}</span>
                        </td>
                        <td className="p-3 text-right">
                          <span className="font-bold text-slate-800">{rec.current_seats} seats</span>
                          <span className="text-[10px] text-slate-400 block">{rec.active_vacancies} postings</span>
                        </td>
                        <td className="p-3 text-center">
                          <span
                            className={`rounded-full px-2 py-0.5 font-bold ${
                              rec.recommended_seat_adjustment > 0
                                ? "bg-emerald-100 text-emerald-800"
                                : rec.recommended_seat_adjustment < 0
                                ? "bg-rose-100 text-rose-800"
                                : "bg-slate-100 text-slate-600"
                            }`}
                          >
                            {rec.recommended_seat_adjustment > 0 ? "+" : ""}
                            {rec.recommended_seat_adjustment}
                          </span>
                        </td>
                        <td className="p-3 text-center">
                          <span className="font-bold text-indigo-700">
                            {rec.recommended_trainer_workshops}
                          </span>
                        </td>
                        <td className="p-3">
                          <span
                            className={`rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider ${
                              rec.equipment_investment_priority === "High"
                                ? "bg-amber-100 text-amber-900 border border-amber-300"
                                : rec.equipment_investment_priority === "Medium"
                                ? "bg-blue-100 text-blue-900"
                                : "bg-slate-100 text-slate-600"
                            }`}
                          >
                            {rec.equipment_investment_priority}
                          </span>
                          <span className="text-[11px] text-slate-600 block mt-0.5 line-clamp-1">
                            {rec.investment_focus}
                          </span>
                        </td>
                        <td className="p-3 text-slate-500 max-w-xs text-[11px] leading-relaxed">
                          {rec.rationale}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </div>

        {/* Footer Actions */}
        <div className="flex flex-wrap items-center justify-between gap-3 border-t border-slate-100 p-4 bg-slate-50 shrink-0">
          <span className="text-[11px] text-slate-400">
            Export compliant with State Skill Mission planning guidelines.
          </span>

          <div className="flex items-center gap-2">
            <button
              onClick={handlePrintReport}
              className="flex items-center gap-1.5 rounded-xl border border-slate-200 bg-white px-3.5 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-100 transition-colors shadow-2xs"
            >
              <Printer className="h-3.5 w-3.5" />
              Print / PDF
            </button>

            <button
              onClick={handleDownloadCSV}
              data-testid="download-csv-btn"
              className="flex items-center gap-1.5 rounded-xl border border-emerald-300 bg-emerald-50 px-3.5 py-2 text-xs font-bold text-emerald-800 hover:bg-emerald-100 transition-colors shadow-2xs"
            >
              <FileSpreadsheet className="h-3.5 w-3.5 text-emerald-700" />
              Export CSV (Excel)
            </button>

            <button
              onClick={handleDownloadJSON}
              data-testid="download-json-btn"
              className="flex items-center gap-1.5 rounded-xl bg-indigo-600 px-4 py-2 text-xs font-bold text-white hover:bg-indigo-700 transition-colors shadow-sm"
            >
              <Download className="h-3.5 w-3.5" />
              Export JSON
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
