import React, { useState } from "react";
import { AlertTriangle, CheckCircle2, Send, X } from "lucide-react";
import { api } from "../../lib/api";

interface TrainerRefresherModalProps {
  isOpen: boolean;
  flagId: string;
  courseName: string;
  tradeName: string;
  onClose: () => void;
  onSuccess: () => void;
}

export const TrainerRefresherModal: React.FC<TrainerRefresherModalProps> = ({
  isOpen,
  flagId,
  courseName,
  tradeName,
  onClose,
  onSuccess,
}) => {
  const [notes, setNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);

    try {
      await api(`/institute/flags/${flagId}/request-trainer-refresher`, {
        method: "POST",
        body: JSON.stringify({
          notes: notes.trim() || undefined,
        }),
      });
      setSubmitted(true);
      setTimeout(() => {
        onSuccess();
        onClose();
        setSubmitted(false);
        setNotes("");
      }, 1500);
    } catch (err: any) {
      setError(err.message || "Failed to submit trainer refresher request");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-sm p-4">
      <div className="w-full max-w-lg rounded-2xl bg-white p-6 shadow-xl border border-slate-100">
        <div className="flex items-start justify-between pb-3 border-b border-slate-100">
          <div>
            <h3 className="text-lg font-bold text-slate-900">
              Request Trainer Refresher Workshop
            </h3>
            <p className="text-xs text-slate-500 mt-0.5">
              Course: <span className="font-semibold text-slate-700">{courseName}</span>
            </p>
          </div>
          <button
            onClick={onClose}
            disabled={submitting}
            className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-600 transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {submitted ? (
          <div className="my-8 flex flex-col items-center justify-center text-center">
            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-emerald-100 text-emerald-600 mb-3">
              <CheckCircle2 className="h-6 w-6" />
            </div>
            <h4 className="text-base font-bold text-slate-900">Request Dispatched</h4>
            <p className="mt-1 text-sm text-slate-600 max-w-sm">
              Your trainer upskilling request has been logged and an in-app alert sent to the District Planning Officer.
            </p>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="mt-4 space-y-4">
            <div className="rounded-lg bg-amber-50/70 border border-amber-200/80 p-3.5">
              <div className="flex gap-2.5">
                <AlertTriangle className="h-5 w-5 text-amber-600 shrink-0 mt-0.5" />
                <div className="text-xs text-amber-800 leading-relaxed">
                  <strong>District Support Pipeline:</strong> This action flags to state & district planners
                  that instructor proficiency needs alignment with newer industrial tools for{" "}
                  <span className="font-semibold">{tradeName}</span>.
                </div>
              </div>
            </div>

            {error && (
              <div className="rounded-lg bg-rose-50 border border-rose-200 p-3 text-xs text-rose-700">
                {error}
              </div>
            )}

            <div>
              <label className="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-1">
                Specific Training Focus / Tooling Notes (Optional)
              </label>
              <textarea
                rows={3}
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="e.g. Need 3-day hands-on refresher on automated diagnostic tools, PLC wiring, or new safety protocols..."
                className="w-full rounded-xl border border-slate-300 p-3 text-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
              />
            </div>

            <div className="flex items-center justify-end gap-3 pt-2">
              <button
                type="button"
                onClick={onClose}
                disabled={submitting}
                className="rounded-xl border border-slate-300 px-4 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50 transition-colors"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={submitting}
                className="flex items-center gap-2 rounded-xl bg-indigo-600 px-5 py-2 text-xs font-semibold text-white shadow-sm hover:bg-indigo-700 disabled:opacity-50 transition-colors"
              >
                {submitting ? (
                  "Submitting..."
                ) : (
                  <>
                    <Send className="h-3.5 w-3.5" />
                    Submit Request
                  </>
                )}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
};
