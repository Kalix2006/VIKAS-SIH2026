import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  AlertCircle,
  CheckCircle2,
  ChevronRight,
  Flame,
  Layers,
  RefreshCw,
  Scale,
  ShieldAlert,
  Vote,
} from "lucide-react";
import { api } from "../../lib/api";

export interface PanelVoteItem {
  id: string;
  panel_review_id: string;
  panel_member_id: string;
  vote: "approve" | "reject" | "abstain";
  comment: string | null;
  voted_at: string;
  panel_role?: string | null;
  voter_name?: string | null;
}

export interface PanelReviewItem {
  id: string;
  skill_gap_id: string;
  track: "urgent" | "standard";
  required_signoffs: number;
  decision: "pending" | "approved" | "rejected";
  veto_used: boolean;
  decided_at: string | null;
  votes: PanelVoteItem[];
  trade_name?: string | null;
  nsqf_code?: string | null;
  district_name?: string | null;
  gap_type?: string | null;
  gap_score?: number | null;
  nlp_confidence?: number | null;
  job_posting_volume?: number | null;
  academic_veto_enabled?: boolean;
}

export interface GovernanceSettings {
  academic_veto_enabled: boolean;
}

export const ReviewQueue: React.FC = () => {
  const [reviews, setReviews] = useState<PanelReviewItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"urgent" | "standard">("urgent");
  const [vetoEnabled, setVetoEnabled] = useState(false);
  const [togglingVeto, setTogglingVeto] = useState(false);

  const fetchQueue = async () => {
    try {
      setLoading(true);
      setError(null);
      const [queueData, govData] = await Promise.all([
        api<PanelReviewItem[]>("/panel/queue"),
        api<GovernanceSettings>("/panel/governance"),
      ]);
      setReviews(queueData);
      setVetoEnabled(govData.academic_veto_enabled);
    } catch (err: any) {
      setError(err.message || "Failed to load panel review queue.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchQueue();
  }, []);

  const handleToggleVeto = async () => {
    try {
      setTogglingVeto(true);
      const res = await api<GovernanceSettings>("/panel/governance/toggle", {
        method: "POST",
        body: JSON.stringify({ enabled: !vetoEnabled }),
      });
      setVetoEnabled(res.academic_veto_enabled);
    } catch (err: any) {
      alert(err.message || "Failed to toggle governance policy");
    } finally {
      setTogglingVeto(false);
    }
  };

  const urgentReviews = reviews.filter((r) => r.track === "urgent");
  const standardReviews = reviews.filter((r) => r.track === "standard");
  const currentReviews = activeTab === "urgent" ? urgentReviews : standardReviews;

  return (
    <div className="space-y-6">
      {/* Header & Governance Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-200 pb-5">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-black tracking-tight text-slate-900">
              Curriculum Governance Queue
            </h1>
            <span className="inline-flex items-center gap-1 rounded-full bg-indigo-50 px-2.5 py-0.5 text-xs font-bold text-indigo-700 border border-indigo-200">
              <Scale className="h-3.5 w-3.5" /> Human-in-the-Loop
            </span>
          </div>
          <p className="mt-1 text-sm text-slate-500">
            Independent tripartite assessment panel reviewing high-divergence trade curricula before formal state notifications.
          </p>
        </div>

        {/* Governance Toggle & Refresh */}
        <div className="flex flex-wrap items-center gap-3">
          {/* Live Governance Toggle Switch */}
          <div
            data-testid="governance-toggle-bar"
            className="flex items-center gap-2.5 rounded-xl border border-slate-200 bg-white px-3.5 py-2 shadow-2xs"
          >
            <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-700">
              <ShieldAlert
                className={`h-4 w-4 ${
                  vetoEnabled ? "text-amber-600 animate-pulse" : "text-slate-400"
                }`}
              />
              <span>Academic Expert Veto:</span>
            </div>
            <button
              onClick={handleToggleVeto}
              disabled={togglingVeto}
              data-testid="academic-veto-toggle-btn"
              className={`relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${
                vetoEnabled ? "bg-amber-600" : "bg-slate-300"
              }`}
            >
              <span
                className={`pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow-sm ring-0 transition duration-200 ease-in-out ${
                  vetoEnabled ? "translate-x-4" : "translate-x-0"
                }`}
              />
            </button>
            <span
              className={`text-[11px] font-bold ${
                vetoEnabled ? "text-amber-700" : "text-slate-500"
              }`}
            >
              {vetoEnabled ? "Active" : "Standard"}
            </span>
          </div>

          <button
            onClick={fetchQueue}
            className="rounded-xl border border-slate-200 p-2 text-slate-500 hover:bg-slate-50 hover:text-slate-700 transition-colors"
            title="Refresh review queue"
          >
            <RefreshCw className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* Academic Veto Active Callout Banner */}
      {vetoEnabled && (
        <div
          data-testid="academic-veto-banner"
          className="rounded-2xl border border-amber-200 bg-amber-50/80 p-4 shadow-xs flex items-start gap-3"
        >
          <ShieldAlert className="h-5 w-5 text-amber-600 shrink-0 mt-0.5" />
          <div className="text-xs text-amber-900 leading-relaxed">
            <strong className="font-bold">Strict Academic Veto Enabled:</strong> Any rejection cast by the{" "}
            <span className="font-bold underline decoration-amber-400">Academic Expert</span> will immediately
            veto and reject the proposal with zero override bypass, ensuring syllabus rigor cannot be diluted by market pressure alone.
          </div>
        </div>
      )}

      {/* Track Selection Tabs */}
      <div className="flex border-b border-slate-200">
        <button
          onClick={() => setActiveTab("urgent")}
          data-testid="tab-urgent-track"
          className={`flex items-center gap-2 py-3 px-5 text-sm font-bold border-b-2 transition-colors ${
            activeTab === "urgent"
              ? "border-rose-600 text-rose-700 bg-rose-50/30"
              : "border-transparent text-slate-500 hover:text-slate-800 hover:border-slate-300"
          }`}
        >
          <Flame className="h-4 w-4 text-rose-600" />
          Urgent Track
          <span
            className={`rounded-full px-2 py-0.5 text-xs font-bold ${
              activeTab === "urgent"
                ? "bg-rose-100 text-rose-800"
                : "bg-slate-100 text-slate-600"
            }`}
          >
            {urgentReviews.length}
          </span>
          <span className="hidden sm:inline text-[11px] font-normal text-slate-400">
            (Requires 2 signoffs)
          </span>
        </button>

        <button
          onClick={() => setActiveTab("standard")}
          data-testid="tab-standard-track"
          className={`flex items-center gap-2 py-3 px-5 text-sm font-bold border-b-2 transition-colors ${
            activeTab === "standard"
              ? "border-indigo-600 text-indigo-700 bg-indigo-50/30"
              : "border-transparent text-slate-500 hover:text-slate-800 hover:border-slate-300"
          }`}
        >
          <Layers className="h-4 w-4 text-indigo-600" />
          Standard Track
          <span
            className={`rounded-full px-2 py-0.5 text-xs font-bold ${
              activeTab === "standard"
                ? "bg-indigo-100 text-indigo-800"
                : "bg-slate-100 text-slate-600"
            }`}
          >
            {standardReviews.length}
          </span>
          <span className="hidden sm:inline text-[11px] font-normal text-slate-400">
            (Requires 4 consensus signoffs)
          </span>
        </button>
      </div>

      {loading && (
        <div className="flex min-h-[300px] flex-col items-center justify-center gap-3">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-indigo-600 border-t-transparent" />
          <p className="text-sm font-medium text-slate-500">Loading governance reviews...</p>
        </div>
      )}

      {error && (
        <div className="rounded-2xl border border-rose-200 bg-rose-50 p-6 text-center">
          <AlertCircle className="mx-auto h-8 w-8 text-rose-500" />
          <p className="mt-2 text-sm font-semibold text-rose-800">{error}</p>
          <button
            onClick={fetchQueue}
            className="mt-3 rounded-lg bg-rose-600 px-4 py-1.5 text-xs font-semibold text-white hover:bg-rose-700"
          >
            Retry
          </button>
        </div>
      )}

      {!loading && !error && currentReviews.length === 0 && (
        <div className="flex min-h-[250px] flex-col items-center justify-center rounded-2xl border-2 border-dashed border-slate-200 p-8 text-center">
          <CheckCircle2 className="h-10 w-10 text-emerald-500" />
          <h3 className="mt-2 text-base font-bold text-slate-800">
            {activeTab === "urgent"
              ? "No urgent reviews pending"
              : "No standard reviews in queue"}
          </h3>
          <p className="mt-1 text-xs text-slate-500 max-w-sm">
            All detected skill divergence items for this review track have been evaluated or resolved.
          </p>
        </div>
      )}

      {!loading && !error && currentReviews.length > 0 && (
        <div className="grid grid-cols-1 gap-4">
          {currentReviews.map((review) => {
            const approveCount = review.votes.filter((v) => v.vote === "approve").length;
            const rejectCount = review.votes.filter((v) => v.vote === "reject").length;
            const totalVoted = review.votes.length;
            const neededSignoffs = review.required_signoffs;

            const isUrgent = review.track === "urgent";
            const tallyLabel = isUrgent
              ? `${approveCount} of ${neededSignoffs} needed`
              : `${totalVoted} of ${neededSignoffs} voted`;

            const percentProgress = isUrgent
              ? Math.min(100, Math.round((approveCount / neededSignoffs) * 100))
              : Math.min(100, Math.round((totalVoted / neededSignoffs) * 100));

            return (
              <div
                key={review.id}
                data-testid={`review-card-${review.id}`}
                className={`group relative overflow-hidden rounded-2xl border transition-all duration-200 bg-white hover:shadow-md ${
                  isUrgent ? "border-rose-200/80 hover:border-rose-300" : "border-slate-200 hover:border-slate-300"
                }`}
              >
                <div className="p-5 md:p-6">
                  <div className="flex flex-col md:flex-row md:items-center justify-between gap-5">
                    {/* Left: Trade & Geographic Scope */}
                    <div className="space-y-2 flex-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <span
                          className={`rounded-full px-2.5 py-0.5 text-xs font-bold uppercase tracking-wider ${
                            isUrgent
                              ? "bg-rose-100 text-rose-800 border border-rose-200"
                              : "bg-indigo-100 text-indigo-800 border border-indigo-200"
                          }`}
                        >
                          {review.track} Track
                        </span>

                        {review.gap_type && (
                          <span className="rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-semibold text-slate-700 capitalize">
                            {review.gap_type.replace("_", " ")}
                          </span>
                        )}

                        {vetoEnabled && (
                          <span
                            data-testid="badge-academic-veto-active"
                            className="inline-flex items-center gap-1 rounded-full bg-amber-100 px-2 py-0.5 text-[10px] font-bold text-amber-900 border border-amber-300"
                          >
                            <ShieldAlert className="h-3 w-3 text-amber-700" />
                            Academic Veto Active
                          </span>
                        )}

                        <span className="text-xs text-slate-400 font-medium">
                          Confidence:{" "}
                          <strong className="text-slate-700">
                            {review.nlp_confidence
                              ? `${Math.round(review.nlp_confidence * 100)}%`
                              : "N/A"}
                          </strong>
                        </span>
                      </div>

                      <div className="flex items-baseline gap-2">
                        <h2 className="text-lg font-bold text-slate-900">
                          {review.trade_name || "Vocational Trade"}
                        </h2>
                        {review.nsqf_code && (
                          <span className="text-xs font-medium text-slate-500">
                            NSQF: {review.nsqf_code}
                          </span>
                        )}
                        <span className="text-slate-300">•</span>
                        <span className="text-sm font-semibold text-slate-600">
                          {review.district_name || "District"} District
                        </span>
                      </div>

                      <div className="flex flex-wrap items-center gap-4 text-xs text-slate-500 pt-1">
                        <span>
                          Gap Score: <strong className="text-slate-900 font-bold">{review.gap_score ?? "N/A"}</strong>
                        </span>
                        <span>
                          Job Vacancies: <strong className="text-slate-900">{review.job_posting_volume ?? 0} postings</strong>
                        </span>
                      </div>
                    </div>

                    {/* Middle: Vote Progress Tally */}
                    <div className="md:w-56 shrink-0 bg-slate-50/80 rounded-xl p-3.5 border border-slate-100">
                      <div className="flex items-center justify-between text-xs mb-1.5">
                        <span className="font-semibold text-slate-700 flex items-center gap-1">
                          <Vote className="h-3.5 w-3.5 text-slate-500" />
                          Vote Tally:
                        </span>
                        <strong className="text-slate-900 font-bold">{tallyLabel}</strong>
                      </div>

                      {/* Progress Bar */}
                      <div className="h-2 w-full rounded-full bg-slate-200 overflow-hidden">
                        <div
                          className={`h-full transition-all duration-300 ${
                            isUrgent ? "bg-rose-500" : "bg-indigo-600"
                          }`}
                          style={{ width: `${percentProgress}%` }}
                        />
                      </div>

                      <div className="flex items-center justify-between text-[11px] text-slate-400 mt-2">
                        <span className="text-emerald-700 font-semibold">{approveCount} approve</span>
                        <span className="text-rose-700 font-semibold">{rejectCount} reject</span>
                        <span>{review.votes.filter((v) => v.vote === "abstain").length} abstain</span>
                      </div>
                    </div>

                    {/* Right: Review Action */}
                    <div className="shrink-0 flex items-center">
                      <Link
                        to={`/panel/reviews/${review.id}`}
                        className={`flex items-center gap-2 rounded-xl px-4 py-2.5 text-xs font-bold text-white shadow-sm transition-colors ${
                          isUrgent
                            ? "bg-rose-600 hover:bg-rose-700 shadow-rose-100"
                            : "bg-indigo-600 hover:bg-indigo-700 shadow-indigo-100"
                        }`}
                      >
                        Review & Vote
                        <ChevronRight className="h-4 w-4" />
                      </Link>
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
