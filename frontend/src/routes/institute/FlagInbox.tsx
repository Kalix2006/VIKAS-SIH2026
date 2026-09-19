import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  AlertCircle,
  CheckCircle,
  ChevronRight,
  GraduationCap,
  RefreshCw,
  Users,
} from "lucide-react";
import { api } from "../../lib/api";
import { TrainerRefresherModal } from "./TrainerRefresherModal";

export interface InstituteFlag {
  flag_id: string;
  course_id: string;
  course_name: string;
  trade_name: string;
  nsqf_code: string;
  seats_available: number;
  course_status: "active" | "flagged" | "obsolete";
  gap_type: string;
  gap_score: number;
  job_posting_volume: number;
  reason: string;
  acknowledged: boolean;
  acknowledged_at?: string | null;
  acknowledged_by_name?: string | null;
  created_at: string;
}

export const FlagInbox: React.FC = () => {
  const [flags, setFlags] = useState<InstituteFlag[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<"all" | "unacknowledged" | "acknowledged">("all");
  const [acknowledgingId, setAcknowledgingId] = useState<string | null>(null);

  // Modal state
  const [selectedFlagForModal, setSelectedFlagForModal] = useState<InstituteFlag | null>(null);

  const fetchFlags = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await api<InstituteFlag[]>("/institute/flags");
      setFlags(data);
    } catch (err: any) {
      setError(err.message || "Failed to load flagged courses.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchFlags();
  }, []);

  const handleAcknowledge = async (flagId: string) => {
    setAcknowledgingId(flagId);
    try {
      await api(`/institute/flags/${flagId}/acknowledge`, {
        method: "POST",
      });
      // Optimistically update local state
      setFlags((prev) =>
        prev.map((f) =>
          f.flag_id === flagId
            ? {
                ...f,
                acknowledged: true,
                acknowledged_at: new Date().toISOString(),
                acknowledged_by_name: "Principal (You)",
              }
            : f
        )
      );
    } catch (err: any) {
      alert(err.message || "Could not acknowledge flag");
    } finally {
      setAcknowledgingId(null);
    }
  };

  const filteredFlags = flags.filter((f) => {
    if (filter === "unacknowledged") return !f.acknowledged;
    if (filter === "acknowledged") return f.acknowledged;
    return true;
  });

  const unackCount = flags.filter((f) => !f.acknowledged).length;

  return (
    <div className="space-y-6">
      {/* Header with KPI and filter tabs */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-200 pb-5">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-black tracking-tight text-slate-900">
              Curriculum Alignment & Flag Inbox
            </h1>
            {unackCount > 0 && (
              <span className="inline-flex items-center rounded-full bg-rose-100 px-2.5 py-0.5 text-xs font-bold text-rose-800 animate-pulse">
                {unackCount} Action Required
              </span>
            )}
          </div>
          <p className="mt-1 text-sm text-slate-500">
            Detected demand divergences and syllabus drift notifications for courses at your institute.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <div className="inline-flex rounded-xl bg-slate-100 p-1 text-xs font-semibold text-slate-600">
            <button
              onClick={() => setFilter("all")}
              className={`rounded-lg px-3 py-1.5 transition-colors ${
                filter === "all" ? "bg-white text-slate-900 shadow-sm" : "hover:text-slate-900"
              }`}
            >
              All ({flags.length})
            </button>
            <button
              onClick={() => setFilter("unacknowledged")}
              className={`rounded-lg px-3 py-1.5 transition-colors ${
                filter === "unacknowledged"
                  ? "bg-rose-600 text-white shadow-sm"
                  : "hover:text-slate-900"
              }`}
            >
              Unacknowledged ({unackCount})
            </button>
            <button
              onClick={() => setFilter("acknowledged")}
              className={`rounded-lg px-3 py-1.5 transition-colors ${
                filter === "acknowledged" ? "bg-white text-slate-900 shadow-sm" : "hover:text-slate-900"
              }`}
            >
              Reviewed ({flags.length - unackCount})
            </button>
          </div>

          <button
            onClick={fetchFlags}
            className="rounded-xl border border-slate-200 p-2 text-slate-500 hover:bg-slate-50 hover:text-slate-700 transition-colors"
            title="Refresh flags"
          >
            <RefreshCw className="h-4 w-4" />
          </button>
        </div>
      </div>

      {loading && (
        <div className="flex min-h-[300px] flex-col items-center justify-center gap-3">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-indigo-600 border-t-transparent" />
          <p className="text-sm font-medium text-slate-500">Loading institute flags...</p>
        </div>
      )}

      {error && (
        <div className="rounded-2xl border border-rose-200 bg-rose-50 p-6 text-center">
          <AlertCircle className="mx-auto h-8 w-8 text-rose-500" />
          <p className="mt-2 text-sm font-semibold text-rose-800">{error}</p>
          <button
            onClick={fetchFlags}
            className="mt-3 rounded-lg bg-rose-600 px-4 py-1.5 text-xs font-semibold text-white hover:bg-rose-700"
          >
            Retry
          </button>
        </div>
      )}

      {!loading && !error && filteredFlags.length === 0 && (
        <div className="flex min-h-[250px] flex-col items-center justify-center rounded-2xl border-2 border-dashed border-slate-200 p-8 text-center">
          <CheckCircle className="h-10 w-10 text-emerald-500" />
          <h3 className="mt-2 text-base font-bold text-slate-800">
            {filter === "unacknowledged"
              ? "All flags acknowledged!"
              : "No flagged courses detected"}
          </h3>
          <p className="mt-1 text-xs text-slate-500 max-w-sm">
            Courses currently offered by your institute are aligned with regional demand parameters.
          </p>
        </div>
      )}

      {!loading && !error && filteredFlags.length > 0 && (
        <div className="grid grid-cols-1 gap-4">
          {filteredFlags.map((flag) => {
            const isUnack = !flag.acknowledged;

            return (
              <div
                key={flag.flag_id}
                data-testid={`flag-card-${flag.flag_id}`}
                className={`group relative overflow-hidden rounded-2xl border transition-all duration-200 ${
                  isUnack
                    ? "border-amber-300/80 bg-amber-50/20 hover:border-amber-400 hover:shadow-md shadow-sm"
                    : "border-slate-200 bg-white hover:border-slate-300 opacity-90"
                }`}
              >
                <div className="p-5 md:p-6">
                  <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
                    {/* Left details */}
                    <div className="space-y-2 flex-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <span
                          className={`rounded-full px-2.5 py-0.5 text-xs font-bold uppercase tracking-wider ${
                            isUnack
                              ? "bg-amber-100 text-amber-900 border border-amber-300"
                              : "bg-slate-100 text-slate-600 border border-slate-200"
                          }`}
                        >
                          {flag.gap_type.replace("_", " ")}
                        </span>

                        <span
                          className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${
                            flag.course_status === "flagged"
                              ? "bg-rose-100 text-rose-800"
                              : "bg-slate-100 text-slate-700"
                          }`}
                        >
                          Status: {flag.course_status}
                        </span>

                        <span className="text-xs text-slate-400 font-medium">
                          Gap Score: <strong className="text-slate-700">{flag.gap_score}</strong>
                        </span>
                      </div>

                      <div className="flex items-baseline gap-2">
                        <h2 className="text-lg font-bold text-slate-900">{flag.course_name}</h2>
                        <span className="text-xs font-medium text-slate-500">
                          NSQF Code: {flag.nsqf_code}
                        </span>
                      </div>

                      {/* Plain language one-line explanation */}
                      <p className="text-sm font-medium text-slate-700 bg-white/70 rounded-xl p-3 border border-slate-100">
                        <span className="font-bold text-slate-900">Diagnosis: </span>
                        {flag.reason}
                      </p>

                      <div className="flex flex-wrap items-center gap-4 text-xs text-slate-500 pt-1">
                        <span className="flex items-center gap-1">
                          <GraduationCap className="h-3.5 w-3.5 text-slate-400" />
                          Seats available: <strong className="text-slate-700">{flag.seats_available}</strong>
                        </span>
                        <span className="flex items-center gap-1">
                          <Users className="h-3.5 w-3.5 text-slate-400" />
                          Local job postings: <strong className="text-slate-700">{flag.job_posting_volume}</strong>
                        </span>
                        {flag.acknowledged && flag.acknowledged_at && (
                          <span className="text-emerald-700 font-medium flex items-center gap-1">
                            <CheckCircle className="h-3.5 w-3.5 text-emerald-600" />
                            Acknowledged by {flag.acknowledged_by_name || "Admin"} on{" "}
                            {new Date(flag.acknowledged_at).toLocaleDateString()}
                          </span>
                        )}
                      </div>
                    </div>

                    {/* Right action buttons */}
                    <div className="flex flex-wrap md:flex-col items-center md:items-end gap-2 shrink-0">
                      {isUnack ? (
                        <button
                          onClick={() => handleAcknowledge(flag.flag_id)}
                          disabled={acknowledgingId === flag.flag_id}
                          className="flex items-center gap-1.5 rounded-xl bg-amber-600 px-4 py-2 text-xs font-bold text-white shadow-sm hover:bg-amber-700 transition-colors disabled:opacity-50"
                        >
                          <CheckCircle className="h-4 w-4" />
                          {acknowledgingId === flag.flag_id ? "Saving..." : "Acknowledge"}
                        </button>
                      ) : (
                        <div className="inline-flex items-center gap-1 rounded-xl bg-emerald-50 px-3 py-1.5 text-xs font-bold text-emerald-700 border border-emerald-200">
                          <CheckCircle className="h-3.5 w-3.5" />
                          Reviewed
                        </div>
                      )}

                      <button
                        onClick={() => setSelectedFlagForModal(flag)}
                        className="rounded-xl border border-indigo-200 bg-indigo-50/60 px-3.5 py-1.5 text-xs font-semibold text-indigo-700 hover:bg-indigo-100 transition-colors"
                      >
                        Request Trainer Refresher
                      </button>

                      <Link
                        to={`/institute/flags/${flag.flag_id}/detail`}
                        className="flex items-center gap-1 rounded-xl border border-slate-200 px-3.5 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50 transition-colors"
                      >
                        Drift Details
                        <ChevronRight className="h-3.5 w-3.5" />
                      </Link>
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Trainer Refresher Request Modal */}
      {selectedFlagForModal && (
        <TrainerRefresherModal
          isOpen={true}
          flagId={selectedFlagForModal.flag_id}
          courseName={selectedFlagForModal.course_name}
          tradeName={selectedFlagForModal.trade_name}
          onClose={() => setSelectedFlagForModal(null)}
          onSuccess={() => {
            // Refetch or update UI
          }}
        />
      )}
    </div>
  );
};
