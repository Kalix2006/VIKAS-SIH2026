import React, { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  ArrowLeft,
  AlertTriangle,
  BookOpen,
  CheckCircle2,
  Sparkles,
  TrendingUp,
} from "lucide-react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import { api } from "../../lib/api";
import { TrainerRefresherModal } from "./TrainerRefresherModal";

interface TrendPoint {
  timestamp: string;
  gap_score: number;
  market_demand_factor: number;
  similarity_score: number;
}

interface DriftDetail {
  flag_id: string;
  course_id: string;
  course_name: string;
  trade_name: string;
  nsqf_code: string;
  gap_type: string;
  gap_score: number;
  reason: string;
  acknowledged: boolean;
  acknowledged_at?: string | null;
  acknowledged_by_name?: string | null;
  score_trend: TrendPoint[];
  skills_drifted: string[];
  syllabus_skills: string[];
  refresher_requested: boolean;
  refresher_request_id?: string | null;
  score_breakdown: Record<string, any>;
}

export const DriftDetailView: React.FC = () => {
  const { flagId } = useParams<{ flagId: string }>();
  const [detail, setDetail] = useState<DriftDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [modalOpen, setModalOpen] = useState(false);

  const fetchDetail = async () => {
    if (!flagId) return;
    try {
      setLoading(true);
      setError(null);
      const data = await api<DriftDetail>(`/institute/flags/${flagId}/detail`);
      setDetail(data);
    } catch (err: any) {
      setError(err.message || "Failed to load drift detail.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDetail();
  }, [flagId]);

  if (loading) {
    return (
      <div className="flex min-h-[400px] flex-col items-center justify-center gap-3">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-indigo-600 border-t-transparent" />
        <p className="text-sm font-medium text-slate-500">Analyzing curriculum drift data...</p>
      </div>
    );
  }

  if (error || !detail) {
    return (
      <div className="rounded-2xl border border-rose-200 bg-rose-50 p-8 text-center">
        <AlertTriangle className="mx-auto h-8 w-8 text-rose-600" />
        <h3 className="mt-2 text-base font-bold text-rose-900">Unable to load details</h3>
        <p className="mt-1 text-sm text-rose-700">{error || "Record not found."}</p>
        <Link
          to="/institute"
          className="mt-4 inline-flex items-center gap-2 rounded-xl bg-slate-900 px-4 py-2 text-xs font-semibold text-white hover:bg-slate-800"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          Back to Flag Inbox
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Navigation & Header */}
      <div>
        <Link
          to="/institute"
          className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-500 hover:text-slate-900 transition-colors mb-2"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          Back to Flag Inbox
        </Link>
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2.5">
              <h1 className="text-2xl font-black tracking-tight text-slate-900">
                Curriculum Drift & Trend Analysis
              </h1>
              <span className="rounded-full bg-indigo-100 px-2.5 py-0.5 text-xs font-bold text-indigo-800 uppercase">
                {detail.gap_type.replace("_", " ")}
              </span>
            </div>
            <p className="mt-1 text-sm text-slate-500">
              {detail.course_name} • NSQF Code: <span className="font-semibold">{detail.nsqf_code}</span>
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => setModalOpen(true)}
              className="flex items-center gap-2 rounded-xl bg-indigo-600 px-4 py-2 text-xs font-bold text-white shadow-sm hover:bg-indigo-700 transition-colors"
            >
              <Sparkles className="h-4 w-4" />
              Request Trainer Refresher
            </button>
          </div>
        </div>
      </div>

      {/* Overview diagnosis banner */}
      <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <div className="flex items-start gap-3">
          <div className="rounded-xl bg-indigo-50 p-2.5 text-indigo-600 shrink-0 mt-0.5">
            <TrendingUp className="h-5 w-5" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-slate-900">Syllabus Drift Summary</h3>
            <p className="mt-1 text-sm text-slate-600 leading-relaxed">{detail.reason}</p>
            <div className="mt-3 flex flex-wrap gap-4 text-xs text-slate-500">
              <span>
                Current Gap Score: <strong className="text-slate-900 text-sm">{detail.gap_score}</strong> / 100
              </span>
              <span>
                Acknowledged:{" "}
                <strong className={detail.acknowledged ? "text-emerald-700" : "text-amber-700"}>
                  {detail.acknowledged ? "Yes" : "Pending Review"}
                </strong>
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Chart Section */}
      <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-slate-100 gap-2">
          <div>
            <h2 className="text-base font-bold text-slate-900">Score & Alignment Progression</h2>
            <p className="text-xs text-slate-500">
              10-week bi-weekly trend tracking the divergence between course syllabus and market demand.
            </p>
          </div>
          <div className="flex items-center gap-3 text-xs">
            <span className="flex items-center gap-1 text-rose-600 font-semibold">
              <span className="h-2 w-2 rounded-full bg-rose-500 inline-block" /> Gap Score (Risk)
            </span>
            <span className="flex items-center gap-1 text-indigo-600 font-semibold">
              <span className="h-2 w-2 rounded-full bg-indigo-500 inline-block" /> Syllabus Alignment
            </span>
          </div>
        </div>

        <div className="h-72 w-full pt-4">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={detail.score_trend}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
              <XAxis dataKey="timestamp" stroke="#94a3b8" fontSize={12} tickLine={false} />
              <YAxis stroke="#94a3b8" fontSize={12} domain={[0, 100]} />
              <Tooltip
                contentStyle={{
                  backgroundColor: "#ffffff",
                  borderRadius: "0.75rem",
                  border: "1px solid #e2e8f0",
                  boxShadow: "0 4px 6px -1px rgb(0 0 0 / 0.1)",
                  fontSize: "12px",
                }}
              />
              <Legend />
              <Line
                type="monotone"
                dataKey="gap_score"
                name="Gap Score"
                stroke="#e11d48"
                strokeWidth={2.5}
                dot={{ r: 4, fill: "#e11d48" }}
                activeDot={{ r: 6 }}
              />
              <Line
                type="monotone"
                dataKey="similarity_score"
                name="Syllabus Similarity (0-1)"
                stroke="#6366f1"
                strokeWidth={2}
                dot={{ r: 3, fill: "#6366f1" }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Skills Divergence Comparison */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Left: Drifted / Missing Skills */}
        <div className="rounded-2xl border border-rose-200 bg-rose-50/30 p-6 shadow-sm">
          <div className="flex items-center gap-2.5 pb-4 border-b border-rose-100">
            <div className="rounded-xl bg-rose-100 p-2 text-rose-700">
              <AlertTriangle className="h-5 w-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-rose-900">Drifted / Emerging Skills Demanded</h3>
              <p className="text-xs text-rose-700">
                Skills required by regional employers that are absent or under-indexed in standard ITI curriculum.
              </p>
            </div>
          </div>

          <div className="mt-4 space-y-2">
            {detail.skills_drifted.map((skill, idx) => (
              <div
                key={idx}
                className="flex items-center justify-between rounded-xl bg-white p-3 border border-rose-200 shadow-2xs"
              >
                <div className="flex items-center gap-2.5">
                  <span className="flex h-6 w-6 items-center justify-center rounded-full bg-rose-100 text-xs font-bold text-rose-700">
                    {idx + 1}
                  </span>
                  <span className="text-sm font-semibold text-slate-800 capitalize">{skill}</span>
                </div>
                <span className="rounded-full bg-rose-100 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-rose-800">
                  Missing
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Right: Covered Syllabus Skills */}
        <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="flex items-center gap-2.5 pb-4 border-b border-slate-100">
            <div className="rounded-xl bg-emerald-50 p-2 text-emerald-600">
              <BookOpen className="h-5 w-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-slate-900">Current Standard Syllabus Competencies</h3>
              <p className="text-xs text-slate-500">Core practical topics currently delivered in this trade.</p>
            </div>
          </div>

          <div className="mt-4 space-y-2">
            {detail.syllabus_skills.map((skill, idx) => (
              <div
                key={idx}
                className="flex items-center justify-between rounded-xl bg-slate-50 p-3 border border-slate-200/80"
              >
                <div className="flex items-center gap-2.5">
                  <CheckCircle2 className="h-4 w-4 text-emerald-600 shrink-0" />
                  <span className="text-sm font-medium text-slate-700 capitalize">{skill}</span>
                </div>
                <span className="rounded-full bg-slate-200 px-2 py-0.5 text-[10px] font-semibold text-slate-700">
                  In Syllabus
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Refresher Modal */}
      <TrainerRefresherModal
        isOpen={modalOpen}
        flagId={detail.flag_id}
        courseName={detail.course_name}
        tradeName={detail.trade_name}
        onClose={() => setModalOpen(false)}
        onSuccess={() => {
          fetchDetail();
        }}
      />
    </div>
  );
};
