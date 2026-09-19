import React, { useState } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  FileEdit,
  ShieldAlert,
  X,
  XCircle,
} from "lucide-react";
import { api } from "../../lib/api";

interface FlagAnnotateModalProps {
  isOpen: boolean;
  onClose: () => void;
  tradeName: string;
  districtName: string;
  gapId: string | null;
  initialNote?: string | null;
  initialOverrideStatus?: string | null;
  onAnnotationSaved: (
    note: string,
    overrideStatus: string | null,
    newGapStatus: string,
  ) => void;
}

export const FlagAnnotateModal: React.FC<FlagAnnotateModalProps> = ({
  isOpen,
  onClose,
  tradeName,
  districtName,
  gapId,
  initialNote,
  initialOverrideStatus,
  onAnnotationSaved,
}) => {
  const [note, setNote] = useState(initialNote || "");
  const [overrideStatus, setOverrideStatus] = useState<string>(
    initialOverrideStatus || "none",
  );
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!gapId) {
      setError("No active skill gap flag to annotate.");
      return;
    }
    if (!note.trim()) {
      setError("Please provide observation notes for the audit trail.");
      return;
    }

    try {
      setLoading(true);
      setError(null);
      const payload: { note: string; override_status?: string | null } = {
        note: note.trim(),
        override_status: overrideStatus === "none" ? null : overrideStatus,
      };

      const res = await api<{
        annotation_id: string;
        note: string;
        override_status: string | null;
        new_gap_status: string;
      }>(`/planner/flags/${gapId}/annotate`, {
        method: "POST",
        body: JSON.stringify(payload),
      });

      onAnnotationSaved(res.note, res.override_status, res.new_gap_status);
      onClose();
    } catch (err: any) {
      setError(err.message || "Failed to record planner annotation.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      data-testid="flag-annotate-modal"
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-xs p-4 font-sans"
    >
      <div className="w-full max-w-lg rounded-3xl border border-slate-200 bg-white p-6 shadow-2xl space-y-5 animate-in fade-in zoom-in-95 duration-150">
        {/* Modal Header */}
        <div className="flex items-start justify-between border-b border-slate-100 pb-4">
          <div>
            <div className="flex items-center gap-2">
              <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-amber-50 text-amber-700 border border-amber-200">
                <FileEdit className="h-4 w-4" />
              </div>
              <h3 className="text-lg font-black tracking-tight text-slate-900">
                Planner Flag Annotation & Override
              </h3>
            </div>
            <p className="text-xs text-slate-500 mt-1">
              {tradeName} • <span className="font-semibold text-slate-700">{districtName} District</span>
            </p>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-600 transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {error && (
          <div className="rounded-xl border border-rose-200 bg-rose-50 p-3 text-xs font-semibold text-rose-800 flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 shrink-0 text-rose-600" />
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Supervisory Note Input */}
          <div>
            <label className="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-1">
              Field Audit Observations & Technical Notes *
            </label>
            <textarea
              rows={3}
              required
              value={note}
              onChange={(e) => setNote(e.target.value)}
              placeholder="e.g. Conducted district industrial liaison; verified local auto cluster requires immediate tooling modernization..."
              className="w-full rounded-xl border border-slate-300 p-3 text-sm focus:border-amber-500 focus:outline-none focus:ring-1 focus:ring-amber-500 shadow-2xs"
            />
          </div>

          {/* Override Radio Selection Cards */}
          <div>
            <label className="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-1.5">
              Supervisory Override Status
            </label>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
              {/* None */}
              <label
                className={`cursor-pointer rounded-xl border p-3 text-xs transition-all ${
                  overrideStatus === "none"
                    ? "border-slate-800 bg-slate-50 font-bold ring-2 ring-slate-800/20"
                    : "border-slate-200 bg-white hover:border-slate-300 text-slate-600"
                }`}
              >
                <div className="flex items-center justify-between mb-1">
                  <span>Standard</span>
                  <input
                    type="radio"
                    name="override_status"
                    value="none"
                    checked={overrideStatus === "none"}
                    onChange={() => setOverrideStatus("none")}
                    className="accent-slate-800"
                  />
                </div>
                <p className="text-[10px] text-slate-400 font-normal">
                  Log observation only; maintain existing workflow.
                </p>
              </label>

              {/* Confirmed */}
              <label
                className={`cursor-pointer rounded-xl border p-3 text-xs transition-all ${
                  overrideStatus === "confirmed"
                    ? "border-amber-600 bg-amber-50/60 font-bold ring-2 ring-amber-600/20 text-amber-950"
                    : "border-slate-200 bg-white hover:border-slate-300 text-slate-600"
                }`}
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="flex items-center gap-1 text-amber-800">
                    <ShieldAlert className="h-3.5 w-3.5" /> Confirm
                  </span>
                  <input
                    type="radio"
                    name="override_status"
                    value="confirmed"
                    checked={overrideStatus === "confirmed"}
                    onChange={() => setOverrideStatus("confirmed")}
                    className="accent-amber-600"
                  />
                </div>
                <p className="text-[10px] text-amber-800/80 font-normal">
                  Confirm high urgency; escalates to urgent review track.
                </p>
              </label>

              {/* Dismissed */}
              <label
                className={`cursor-pointer rounded-xl border p-3 text-xs transition-all ${
                  overrideStatus === "dismissed"
                    ? "border-rose-600 bg-rose-50/60 font-bold ring-2 ring-rose-600/20 text-rose-950"
                    : "border-slate-200 bg-white hover:border-slate-300 text-slate-600"
                }`}
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="flex items-center gap-1 text-rose-800">
                    <XCircle className="h-3.5 w-3.5" /> Dismiss
                  </span>
                  <input
                    type="radio"
                    name="override_status"
                    value="dismissed"
                    checked={overrideStatus === "dismissed"}
                    onChange={() => setOverrideStatus("dismissed")}
                    className="accent-rose-600"
                  />
                </div>
                <p className="text-[10px] text-rose-800/80 font-normal">
                  Dismiss flag as false positive or locally mitigated.
                </p>
              </label>
            </div>
          </div>

          {/* Modal Actions */}
          <div className="flex items-center justify-end gap-2.5 pt-3 border-t border-slate-100">
            <button
              type="button"
              onClick={onClose}
              className="rounded-xl border border-slate-200 px-4 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-50 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="flex items-center gap-1.5 rounded-xl bg-amber-600 px-5 py-2 text-xs font-bold text-white hover:bg-amber-700 transition-colors shadow-sm disabled:opacity-50"
            >
              {loading ? (
                "Saving..."
              ) : (
                <>
                  <CheckCircle2 className="h-4 w-4" />
                  Save Annotation
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

