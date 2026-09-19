import React, { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  AlertTriangle,
  ArrowLeft,
  CheckCircle,
  CheckCircle2,
  Clock,
  Info,
  Scale,
  Send,
  ShieldAlert,
  Users,
  Vote,
  XCircle,
} from "lucide-react";
import { api } from "../../lib/api";
import { useAuth } from "../../lib/auth";
import { PanelReviewItem } from "./ReviewQueue";

interface ScoreBreakdownDetail {
  skill_gap_id: string;
  gap_score: number;
  nlp_confidence: number;
  gap_type: string;
  job_posting_volume: number;
  trade_name?: string | null;
  district_name?: string | null;
  score_breakdown: {
    similarity_score?: number;
    dissimilarity?: number;
    volume?: number;
    volume_factor?: number;
    volume_weight?: number;
    avg_age_days?: number;
    recency_decay?: number;
    recency_weight?: number;
    market_demand_factor?: number;
    final_gap_score?: number;
    gap_type?: string;
    seats_available?: number;
    formula?: string;
    [key: string]: any;
  };
}

export const ReviewDetailView: React.FC = () => {
  const { reviewId } = useParams<{ reviewId: string }>();
  const { user } = useAuth();

  const [review, setReview] = useState<PanelReviewItem | null>(null);
  const [breakdown, setBreakdown] = useState<ScoreBreakdownDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Voting form state
  const [selectedVote, setSelectedVote] = useState<"approve" | "reject" | "abstain">("approve");
  const [comment, setComment] = useState("");
  const [submittingVote, setSubmittingVote] = useState(false);
  const [voteSuccessMessage, setVoteSuccessMessage] = useState<string | null>(null);

  const fetchReviewDetails = async () => {
    if (!reviewId) return;
    try {
      setLoading(true);
      setError(null);
      const [reviewData, breakdownData] = await Promise.all([
        api<PanelReviewItem>(`/panel/reviews/${reviewId}`),
        api<ScoreBreakdownDetail>(`/panel/reviews/${reviewId}/score-breakdown`),
      ]);
      setReview(reviewData);
      setBreakdown(breakdownData);
    } catch (err: any) {
      setError(err.message || "Failed to load review details.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchReviewDetails();
  }, [reviewId]);

  const handleCastVote = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!reviewId) return;
    try {
      setSubmittingVote(true);
      setError(null);
      const updatedReview = await api<PanelReviewItem>(`/panel/reviews/${reviewId}/vote`, {
        method: "POST",
        body: JSON.stringify({
          vote: selectedVote,
          comment: comment.trim() || null,
        }),
      });

      // Optimistically update review state with the newly finalized/updated review
      setReview(updatedReview);
      setVoteSuccessMessage(
        updatedReview.decision === "approved"
          ? "Vote recorded! Signoff requirement satisfied — Proposal is now APPROVED."
          : updatedReview.decision === "rejected"
          ? "Vote recorded! Proposal has been REJECTED."
          : "Your vote has been successfully cast."
      );
    } catch (err: any) {
      setError(err.message || "Failed to record vote.");
    } finally {
      setSubmittingVote(false);
    }
  };

  if (loading) {
    return (
      <div className="flex min-h-[400px] flex-col items-center justify-center gap-3 font-sans">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-indigo-600 border-t-transparent" />
        <p className="text-sm font-medium text-slate-500">Loading audit breakdown & votes...</p>
      </div>
    );
  }

  if (error && !review) {
    return (
      <div className="rounded-2xl border border-rose-200 bg-rose-50 p-8 text-center font-sans">
        <AlertTriangle className="mx-auto h-8 w-8 text-rose-600" />
        <h3 className="mt-2 text-base font-bold text-rose-900">Review not found</h3>
        <p className="mt-1 text-sm text-rose-700">{error}</p>
        <Link
          to="/panel"
          className="mt-4 inline-flex items-center gap-2 rounded-xl bg-slate-900 px-4 py-2 text-xs font-semibold text-white hover:bg-slate-800"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          Back to Queue
        </Link>
      </div>
    );
  }

  if (!review) return null;

  const isUrgent = review.track === "urgent";
  const vetoEnabled = review.academic_veto_enabled;
  const isPending = review.decision === "pending";
  const isApproved = review.decision === "approved";
  const isRejected = review.decision === "rejected";

  const userVote = review.votes.find((v) => v.panel_member_id === user?.id);
  const hasUserVoted = !!userVote;

  // Determine current voter's panel role for veto warning styling
  const isAcademicExpertUser =
    user?.email?.includes("expert") || user?.full_name?.toLowerCase().includes("academic");

  // Math components from score breakdown
  const sb = breakdown?.score_breakdown || {};
  const simScore = sb.similarity_score ?? 0.5;
  const dissim = sb.dissimilarity ?? Number((1 - simScore).toFixed(4));
  const rawVol = sb.volume ?? review.job_posting_volume ?? 0;
  const volFactor = sb.volume_factor ?? 0.8;
  const volWeight = sb.volume_weight ?? 0.6;
  const avgAge = sb.avg_age_days ?? 15.0;
  const recencyDecay = sb.recency_decay ?? 0.74;
  const recencyWeight = sb.recency_weight ?? 0.4;
  const marketDemand = sb.market_demand_factor ?? Number((volWeight * volFactor + recencyWeight * recencyDecay).toFixed(4));
  const finalScore = sb.final_gap_score ?? review.gap_score ?? 0;

  return (
    <div className="space-y-6 font-sans">
      {/* Navigation & Header */}
      <div>
        <Link
          to="/panel"
          className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-500 hover:text-slate-900 transition-colors mb-2"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          Back to Review Queue
        </Link>

        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex flex-wrap items-center gap-2.5">
              <h1 className="text-2xl font-black tracking-tight text-slate-900">
                {review.trade_name || "Vocational Trade"}
              </h1>

              <span
                className={`rounded-full px-2.5 py-0.5 text-xs font-bold uppercase tracking-wider ${
                  isUrgent ? "bg-rose-100 text-rose-800" : "bg-indigo-100 text-indigo-800"
                }`}
              >
                {review.track} Track ({review.required_signoffs} Signoffs Needed)
              </span>

              {/* Live Decision Badge */}
              <span
                data-testid="badge-review-decision"
                className={`rounded-full px-3 py-0.5 text-xs font-bold uppercase tracking-wider ${
                  isApproved
                    ? "bg-emerald-100 text-emerald-800 border border-emerald-300"
                    : isRejected
                    ? "bg-rose-100 text-rose-800 border border-rose-300"
                    : "bg-amber-100 text-amber-800 border border-amber-300"
                }`}
              >
                Status: {review.decision}
              </span>

              {review.veto_used && (
                <span
                  data-testid="badge-veto-used"
                  className="rounded-full bg-rose-600 px-2.5 py-0.5 text-xs font-bold text-white shadow-xs flex items-center gap-1"
                >
                  <ShieldAlert className="h-3 w-3" />
                  Academic Veto Exercised
                </span>
              )}
            </div>

            <p className="mt-1 text-sm text-slate-500">
              District: <span className="font-semibold text-slate-700">{review.district_name || "Pune"}</span> •
              Gap Type: <span className="font-semibold capitalize text-slate-700">{review.gap_type?.replace("_", " ")}</span>
            </p>
          </div>

          <div className="flex items-center gap-3">
            <div className="rounded-xl border border-slate-200 bg-white px-4 py-2 text-right shadow-2xs">
              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block">
                Urgency Threshold
              </span>
              <span className="text-xs font-bold text-slate-800">
                {isUrgent ? "2 of 4 Approvals" : "4 of 4 Consensus"}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Veto Callout if Veto is active */}
      {vetoEnabled && (
        <div
          data-testid="governance-veto-alert"
          className="rounded-2xl border border-amber-300 bg-amber-50/90 p-4 shadow-2xs flex items-start gap-3"
        >
          <ShieldAlert className="h-5 w-5 text-amber-600 shrink-0 mt-0.5" />
          <div className="text-xs text-amber-900 leading-relaxed flex-1">
            <strong className="font-bold">Active Governance Override Protocol:</strong> Academic Expert veto authority
            is <strong className="text-amber-950 underline">ENABLED</strong> for this session. Rejection by an Academic Expert
            will immediately override majority signoffs and reject the proposed curriculum escalation.
          </div>
        </div>
      )}

      {/* Success Banner if vote just submitted */}
      {voteSuccessMessage && (
        <div
          data-testid="vote-success-banner"
          className="rounded-2xl border border-emerald-200 bg-emerald-50 p-4 flex items-center gap-3 text-sm font-semibold text-emerald-800"
        >
          <CheckCircle2 className="h-5 w-5 text-emerald-600 shrink-0" />
          {voteSuccessMessage}
        </div>
      )}

      {/* ========================================================================= */}
      {/* SECTION 1: "NOT A BLACK BOX" AUDITABLE MATHEMATICAL SCORE BREAKDOWN       */}
      {/* ========================================================================= */}
      <div
        data-testid="score-breakdown-container"
        className="rounded-3xl border border-slate-200 bg-white p-6 md:p-8 shadow-sm space-y-6"
      >
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 border-b border-slate-100 pb-4">
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-lg font-black tracking-tight text-slate-900">
                Auditable Algorithmic Breakdown
              </h2>
              <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-bold text-slate-600 uppercase">
                Deterministic • Zero LLM
              </span>
            </div>
            <p className="text-xs text-slate-500 mt-0.5">
              Empirical formula computed directly from vector cosine similarities, logged vacancy volumes, and half-life recency decay.
            </p>
          </div>

          <div className="inline-flex items-center gap-2 rounded-xl bg-slate-900 px-4 py-2 text-white shadow-2xs">
            <span className="text-xs text-slate-300">Composite Gap Score:</span>
            <span data-testid="final-gap-score-value" className="text-lg font-black tracking-tight text-emerald-400">
              {finalScore}
            </span>
            <span className="text-xs text-slate-400">/ 100</span>
          </div>
        </div>

        {/* Formula Display Banner */}
        <div className="rounded-2xl border border-indigo-100 bg-indigo-50/50 p-4">
          <div className="flex items-center gap-2 text-xs font-bold text-indigo-900 uppercase tracking-wider mb-1">
            <Scale className="h-4 w-4 text-indigo-600" />
            Statutory Gap Score Formula
          </div>
          <code
            data-testid="formula-text"
            className="block text-xs md:text-sm font-mono text-indigo-950 font-semibold bg-white/80 p-2.5 rounded-xl border border-indigo-200/70"
          >
            Final Gap Score = 100 × (1 - S) × [0.60 × F_V + 0.40 × R]
          </code>
        </div>

        {/* 3 Constituent Factor Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
          {/* Factor 1: Curriculum Alignment */}
          <div
            data-testid="component-dissimilarity-card"
            className="rounded-2xl border border-slate-200 bg-slate-50/50 p-5 space-y-3"
          >
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-500">
                1. Curriculum Divergence
              </span>
              <span className="rounded-full bg-blue-100 px-2 py-0.5 text-[10px] font-bold text-blue-800">
                Complement (1 - S)
              </span>
            </div>

            <div>
              <div className="flex items-baseline justify-between">
                <span className="text-2xl font-black text-slate-900" data-testid="dissimilarity-value">
                  {dissim}
                </span>
                <span className="text-xs text-slate-500">
                  Cosine Sim (S): <strong className="text-slate-700">{simScore}</strong>
                </span>
              </div>
              <p className="text-[11px] text-slate-500 mt-1 leading-snug">
                Semantic distance between standard NSQF syllabus and extracted employer vacancy skills.
              </p>
            </div>

            <div className="h-1.5 w-full rounded-full bg-slate-200 overflow-hidden">
              <div
                className="h-full bg-blue-600 rounded-full"
                style={{ width: `${Math.round(dissim * 100)}%` }}
              />
            </div>
            <div className="text-[10px] font-semibold text-slate-400 flex justify-between">
              <span>0.0 (Aligned)</span>
              <span>1.0 (Total Divergence)</span>
            </div>
          </div>

          {/* Factor 2: Logarithmic Volume Factor */}
          <div
            data-testid="component-volume-card"
            className="rounded-2xl border border-slate-200 bg-slate-50/50 p-5 space-y-3"
          >
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-500">
                2. Vacancy Volume (F_V)
              </span>
              <span className="rounded-full bg-purple-100 px-2 py-0.5 text-[10px] font-bold text-purple-800">
                Weight: 60%
              </span>
            </div>

            <div>
              <div className="flex items-baseline justify-between">
                <span className="text-2xl font-black text-slate-900" data-testid="volume-factor-value">
                  {volFactor}
                </span>
                <span className="text-xs text-slate-500">
                  Raw Volume: <strong className="text-slate-700">{rawVol} jobs</strong>
                </span>
              </div>
              <p className="text-[11px] text-slate-500 mt-1 leading-snug">
                Scaled logarithmically: <code className="text-slate-700">ln(1 + V) / ln(101)</code> to mitigate spike distortions.
              </p>
            </div>

            <div className="h-1.5 w-full rounded-full bg-slate-200 overflow-hidden">
              <div
                className="h-full bg-purple-600 rounded-full"
                style={{ width: `${Math.round(volFactor * 100)}%` }}
              />
            </div>
            <div className="text-[10px] font-semibold text-slate-400 flex justify-between">
              <span>Weighted Contribution:</span>
              <strong className="text-purple-700">{(volFactor * volWeight).toFixed(3)}</strong>
            </div>
          </div>

          {/* Factor 3: Empirical Recency Decay */}
          <div
            data-testid="component-recency-card"
            className="rounded-2xl border border-slate-200 bg-slate-50/50 p-5 space-y-3"
          >
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-500">
                3. Recency Decay (R)
              </span>
              <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-[10px] font-bold text-emerald-800">
                Weight: 40%
              </span>
            </div>

            <div>
              <div className="flex items-baseline justify-between">
                <span className="text-2xl font-black text-slate-900" data-testid="recency-decay-value">
                  {recencyDecay}
                </span>
                <span className="text-xs text-slate-500">
                  Avg Age: <strong className="text-slate-700">{avgAge}d</strong>
                </span>
              </div>
              <p className="text-[11px] text-slate-500 mt-1 leading-snug">
                Exponential decay: <code className="text-slate-700">exp(-0.02 × t)</code> modeling a 35-day half-life.
              </p>
            </div>

            <div className="h-1.5 w-full rounded-full bg-slate-200 overflow-hidden">
              <div
                className="h-full bg-emerald-600 rounded-full"
                style={{ width: `${Math.round(recencyDecay * 100)}%` }}
              />
            </div>
            <div className="text-[10px] font-semibold text-slate-400 flex justify-between">
              <span>Weighted Contribution:</span>
              <strong className="text-emerald-700">{(recencyDecay * recencyWeight).toFixed(3)}</strong>
            </div>
          </div>
        </div>

        {/* Combined Market Factor Summary Strip */}
        <div className="flex flex-col sm:flex-row items-center justify-between rounded-2xl bg-slate-100 p-4 text-xs font-medium text-slate-700 gap-3">
          <div className="flex items-center gap-2">
            <Info className="h-4 w-4 text-slate-500" />
            <span>
              Combined Regional Market Demand Factor:{" "}
              <strong className="text-slate-900">[0.60 × {volFactor} + 0.40 × {recencyDecay}] = {marketDemand}</strong>
            </span>
          </div>
          <div className="text-slate-500">
            Calculation: <code className="font-mono text-slate-800">100 × {dissim} × {marketDemand} = {finalScore}</code>
          </div>
        </div>
      </div>

      {/* ========================================================================= */}
      {/* SECTION 2: VOTING STATION (CAST VOTE)                                    */}
      {/* ========================================================================= */}
      <div className="rounded-3xl border border-slate-200 bg-white p-6 md:p-8 shadow-sm space-y-5">
        <div className="border-b border-slate-100 pb-4">
          <h2 className="text-lg font-black tracking-tight text-slate-900 flex items-center gap-2">
            <Vote className="h-5 w-5 text-indigo-600" />
            Panel Member Voting Station
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Cast your official vote to confirm, revise, or reject this proposed regional curriculum realignment.
          </p>
        </div>

        {hasUserVoted ? (
          <div
            data-testid="already-voted-notice"
            className="rounded-2xl border border-emerald-200 bg-emerald-50/70 p-5 flex items-center gap-4"
          >
            <CheckCircle className="h-6 w-6 text-emerald-600 shrink-0" />
            <div>
              <h4 className="text-sm font-bold text-emerald-950">Vote Recorded</h4>
              <p className="text-xs text-emerald-800 mt-0.5">
                You have already submitted your official vote ({userVote.vote.toUpperCase()}) on this proposal.
                {userVote.comment && ` Remarks: "${userVote.comment}"`}
              </p>
            </div>
          </div>
        ) : !isPending ? (
          <div className="rounded-2xl border border-slate-200 bg-slate-50 p-5 text-xs text-slate-600">
            This review has concluded and is finalized as <strong className="uppercase font-bold text-slate-900">{review.decision}</strong>.
            Further votes cannot be accepted.
          </div>
        ) : (
          <form onSubmit={handleCastVote} className="space-y-5" data-testid="vote-form">
            {/* Vote Choice Radio Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              {/* Approve Choice */}
              <label
                className={`flex cursor-pointer flex-col rounded-2xl border p-4 transition-all ${
                  selectedVote === "approve"
                    ? "border-emerald-500 bg-emerald-50/50 shadow-sm ring-2 ring-emerald-500/20"
                    : "border-slate-200 hover:border-slate-300 bg-white"
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold uppercase tracking-wider text-emerald-800 flex items-center gap-1.5">
                    <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                    Approve
                  </span>
                  <input
                    type="radio"
                    name="voteChoice"
                    value="approve"
                    checked={selectedVote === "approve"}
                    onChange={() => setSelectedVote("approve")}
                    className="accent-emerald-600"
                  />
                </div>
                <p className="text-xs text-slate-500 mt-2">
                  Validate the divergence findings and authorize institutional curriculum modernization.
                </p>
              </label>

              {/* Reject Choice */}
              <label
                className={`flex cursor-pointer flex-col rounded-2xl border p-4 transition-all ${
                  selectedVote === "reject"
                    ? "border-rose-500 bg-rose-50/50 shadow-sm ring-2 ring-rose-500/20"
                    : "border-slate-200 hover:border-slate-300 bg-white"
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold uppercase tracking-wider text-rose-800 flex items-center gap-1.5">
                    <XCircle className="h-4 w-4 text-rose-600" />
                    Reject {vetoEnabled && isAcademicExpertUser && "(VETO)"}
                  </span>
                  <input
                    type="radio"
                    name="voteChoice"
                    value="reject"
                    checked={selectedVote === "reject"}
                    onChange={() => setSelectedVote("reject")}
                    className="accent-rose-600"
                  />
                </div>
                <p className="text-xs text-slate-500 mt-2">
                  {vetoEnabled && isAcademicExpertUser ? (
                    <strong className="text-rose-700 font-bold block">
                      ⚠ Exercises statutory Academic Veto: will immediately reject the proposal.
                    </strong>
                  ) : (
                    "Reject divergence finding due to syllabus sufficiency or unrepresentative employer data."
                  )}
                </p>
              </label>

              {/* Abstain Choice */}
              <label
                className={`flex cursor-pointer flex-col rounded-2xl border p-4 transition-all ${
                  selectedVote === "abstain"
                    ? "border-slate-500 bg-slate-100 shadow-sm ring-2 ring-slate-400/20"
                    : "border-slate-200 hover:border-slate-300 bg-white"
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold uppercase tracking-wider text-slate-800 flex items-center gap-1.5">
                    <Clock className="h-4 w-4 text-slate-600" />
                    Abstain
                  </span>
                  <input
                    type="radio"
                    name="voteChoice"
                    value="abstain"
                    checked={selectedVote === "abstain"}
                    onChange={() => setSelectedVote("abstain")}
                    className="accent-slate-600"
                  />
                </div>
                <p className="text-xs text-slate-500 mt-2">
                  Abstain from voting due to domain conflict or insufficient local trade context.
                </p>
              </label>
            </div>

            {/* Optional Remarks Textarea */}
            <div>
              <label className="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-1">
                Governance Remarks / Technical Justification (Optional)
              </label>
              <textarea
                rows={2}
                value={comment}
                onChange={(e) => setComment(e.target.value)}
                placeholder="e.g. Reviewed lab tooling requirements; recommend sanctioning modern welding equipment..."
                className="w-full rounded-xl border border-slate-300 p-3 text-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
              />
            </div>

            {/* Submit Action */}
            <div className="flex items-center justify-end gap-3 pt-2">
              <button
                type="submit"
                disabled={submittingVote}
                data-testid="submit-vote-btn"
                className="flex items-center gap-2 rounded-xl bg-indigo-600 px-6 py-2.5 text-xs font-bold text-white shadow-sm hover:bg-indigo-700 transition-colors disabled:opacity-50"
              >
                {submittingVote ? (
                  "Submitting Vote..."
                ) : (
                  <>
                    <Send className="h-3.5 w-3.5" />
                    Cast Official Vote
                  </>
                )}
              </button>
            </div>
          </form>
        )}
      </div>

      {/* ========================================================================= */}
      {/* SECTION 3: PANEL MEMBERS VOTES LOG & AUDIT RECORD                        */}
      {/* ========================================================================= */}
      <div className="rounded-3xl border border-slate-200 bg-white p-6 md:p-8 shadow-sm space-y-4">
        <div className="flex items-center justify-between border-b border-slate-100 pb-3">
          <div className="flex items-center gap-2">
            <Users className="h-5 w-5 text-indigo-600" />
            <h3 className="text-base font-bold text-slate-900">
              Panel Votes Audit Trail ({review.votes.length} cast)
            </h3>
          </div>
          <span className="text-xs font-medium text-slate-500">
            Target Signoffs: <strong className="text-slate-800">{review.required_signoffs}</strong>
          </span>
        </div>

        {review.votes.length === 0 ? (
          <p className="text-xs text-slate-400 py-4 text-center">
            No votes have been recorded on this proposal yet. Be the first to cast a vote.
          </p>
        ) : (
          <div className="space-y-3" data-testid="votes-audit-list">
            {review.votes.map((v) => {
              const isApprove = v.vote === "approve";
              const isReject = v.vote === "reject";
              const isVetoVote = isReject && v.panel_role === "academic_expert" && review.veto_used;

              return (
                <div
                  key={v.id}
                  className={`flex flex-col sm:flex-row sm:items-center justify-between gap-3 rounded-2xl border p-4 transition-all ${
                    isVetoVote
                      ? "border-rose-400 bg-rose-50/70"
                      : "border-slate-100 bg-slate-50/60"
                  }`}
                >
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-bold text-slate-900">
                        {v.voter_name || "Panel Member"}
                      </span>
                      {v.panel_role && (
                        <span
                          data-testid={`badge-role-${v.panel_role}`}
                          className="rounded-full bg-slate-200 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-slate-700"
                        >
                          {v.panel_role.replace("_", " ")}
                        </span>
                      )}
                      {isVetoVote && (
                        <span className="rounded-full bg-rose-600 px-2 py-0.5 text-[10px] font-bold text-white flex items-center gap-1">
                          <ShieldAlert className="h-3 w-3" />
                          Academic Veto
                        </span>
                      )}
                    </div>
                    {v.comment && (
                      <p className="text-xs text-slate-600 italic">
                        "{v.comment}"
                      </p>
                    )}
                    <span className="text-[10px] text-slate-400 block">
                      Voted at: {new Date(v.voted_at).toLocaleString()}
                    </span>
                  </div>

                  <div className="shrink-0">
                    <span
                      className={`inline-flex items-center gap-1 rounded-xl px-3 py-1.5 text-xs font-bold ${
                        isApprove
                          ? "bg-emerald-100 text-emerald-800 border border-emerald-300"
                          : isReject
                          ? "bg-rose-100 text-rose-800 border border-rose-300"
                          : "bg-slate-200 text-slate-700"
                      }`}
                    >
                      {isApprove && <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600" />}
                      {isReject && <XCircle className="h-3.5 w-3.5 text-rose-600" />}
                      {v.vote.toUpperCase()}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};
