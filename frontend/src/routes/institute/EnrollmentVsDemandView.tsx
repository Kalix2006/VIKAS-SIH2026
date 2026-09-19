import React, { useEffect, useState } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import {
  AlertCircle,
  Building2,
  RefreshCw,
  TrendingUp,
} from "lucide-react";
import { api } from "../../lib/api";

interface CourseDemandComparison {
  course_id: string;
  course_name: string;
  trade_name: string;
  seats_available: number;
  job_posting_volume: number;
  ratio: number;
  recommendation: string;
  course_status: "active" | "flagged" | "obsolete";
}

interface EnrollmentVsDemandData {
  institute_id: string;
  institute_name: string;
  district_name: string;
  courses: CourseDemandComparison[];
  summary: string;
}

export const EnrollmentVsDemandView: React.FC = () => {
  const [data, setData] = useState<EnrollmentVsDemandData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await api<EnrollmentVsDemandData>("/institute/enrollment-vs-demand");
      setData(res);
    } catch (err: any) {
      setError(err.message || "Failed to load enrollment vs demand analytics.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  if (loading) {
    return (
      <div className="flex min-h-[400px] flex-col items-center justify-center gap-3">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-indigo-600 border-t-transparent" />
        <p className="text-sm font-medium text-slate-500">Aggregating capacity vs market demand...</p>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="rounded-2xl border border-rose-200 bg-rose-50 p-8 text-center">
        <AlertCircle className="mx-auto h-8 w-8 text-rose-500" />
        <h3 className="mt-2 text-base font-bold text-rose-800">Failed to load analytics</h3>
        <p className="mt-1 text-sm text-rose-600">{error || "No data available."}</p>
        <button
          onClick={fetchData}
          className="mt-4 rounded-xl bg-rose-600 px-4 py-2 text-xs font-semibold text-white hover:bg-rose-700"
        >
          Retry
        </button>
      </div>
    );
  }

  // Chart data formatting
  const chartData = data.courses.map((c) => ({
    name: c.trade_name,
    seats: c.seats_available,
    jobs: c.job_posting_volume,
    ratio: c.ratio,
  }));

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-200 pb-5">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-2xl font-black tracking-tight text-slate-900">
              Enrollment vs. Industry Demand
            </h1>
            <span className="rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-bold text-slate-700">
              {data.district_name}
            </span>
          </div>
          <p className="mt-1 text-sm text-slate-500">
            Compare student seating capacity against active local hiring openings to inform intake adjustments.
          </p>
        </div>

        <button
          onClick={fetchData}
          className="flex items-center gap-1.5 self-start md:self-auto rounded-xl border border-slate-200 px-3.5 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-50 transition-colors"
        >
          <RefreshCw className="h-3.5 w-3.5" />
          Refresh Analytics
        </button>
      </div>

      {/* Summary KPI Banner */}
      <div className="rounded-2xl border border-indigo-100 bg-linear-to-r from-indigo-50/70 to-slate-50 p-6 shadow-sm">
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
          <div className="flex items-start gap-3">
            <div className="rounded-xl bg-indigo-600 p-2.5 text-white shrink-0 mt-0.5">
              <Building2 className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-slate-900">{data.institute_name}</h2>
              <p className="text-xs text-slate-600 mt-0.5">{data.summary}</p>
            </div>
          </div>

          <div className="flex items-center gap-4 text-xs">
            <div className="rounded-xl bg-white p-3 border border-slate-200 shadow-2xs text-center min-w-[100px]">
              <span className="text-slate-400 font-medium block">Total Seats</span>
              <strong className="text-lg font-black text-slate-900">
                {data.courses.reduce((acc, curr) => acc + curr.seats_available, 0)}
              </strong>
            </div>
            <div className="rounded-xl bg-white p-3 border border-slate-200 shadow-2xs text-center min-w-[100px]">
              <span className="text-slate-400 font-medium block">Active Jobs</span>
              <strong className="text-lg font-black text-indigo-600">
                {data.courses.reduce((acc, curr) => acc + curr.job_posting_volume, 0)}
              </strong>
            </div>
          </div>
        </div>
      </div>

      {/* Comparison Chart */}
      <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-slate-100 gap-2">
          <div>
            <h2 className="text-base font-bold text-slate-900">Trade Capacity vs. Hiring Volume</h2>
            <p className="text-xs text-slate-500">
              Blue bars represent sanctioned student intake; violet bars represent recent employer job vacancies.
            </p>
          </div>
          <div className="flex items-center gap-4 text-xs font-semibold">
            <span className="flex items-center gap-1.5 text-slate-600">
              <span className="h-3 w-3 rounded-xs bg-slate-700 inline-block" /> Sanctioned Seats
            </span>
            <span className="flex items-center gap-1.5 text-indigo-600">
              <span className="h-3 w-3 rounded-xs bg-indigo-600 inline-block" /> Job Postings
            </span>
          </div>
        </div>

        <div className="h-80 w-full pt-4">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} margin={{ top: 20, right: 30, left: 0, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
              <XAxis dataKey="name" stroke="#64748b" fontSize={12} tickLine={false} />
              <YAxis stroke="#64748b" fontSize={12} tickLine={false} axisLine={false} />
              <Tooltip
                contentStyle={{
                  backgroundColor: "#ffffff",
                  borderRadius: "0.75rem",
                  border: "1px solid #e2e8f0",
                  boxShadow: "0 4px 6px -1px rgb(0 0 0 / 0.1)",
                  fontSize: "12px",
                }}
              />
              <Bar dataKey="seats" name="Sanctioned Seats" fill="#334155" radius={[4, 4, 0, 0]} />
              <Bar dataKey="jobs" name="Active Vacancies" fill="#4f46e5" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Course Breakdown Table */}
      <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
        <div className="p-5 border-b border-slate-100">
          <h3 className="text-base font-bold text-slate-900">Capacity Assessment & Guidance</h3>
          <p className="text-xs text-slate-500 mt-0.5">
            Prescriptive recommendations based on job-to-seat demand ratios.
          </p>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm text-slate-600">
            <thead className="bg-slate-50/80 text-xs font-bold uppercase tracking-wider text-slate-500 border-b border-slate-200">
              <tr>
                <th className="px-5 py-3.5">Course / Trade</th>
                <th className="px-4 py-3.5 text-center">Sanctioned Seats</th>
                <th className="px-4 py-3.5 text-center">Active Jobs</th>
                <th className="px-4 py-3.5 text-center">Demand Ratio</th>
                <th className="px-5 py-3.5">Capacity Recommendation</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {data.courses.map((course) => {
                const isHigh = course.ratio >= 1.5;
                const isLow = course.ratio <= 0.5;

                return (
                  <tr key={course.course_id} className="hover:bg-slate-50/60 transition-colors">
                    <td className="px-5 py-4 font-semibold text-slate-900">
                      <div>{course.course_name}</div>
                      <span className="text-[11px] font-normal text-slate-400 capitalize">
                        Status: {course.course_status}
                      </span>
                    </td>
                    <td className="px-4 py-4 text-center font-bold text-slate-800">
                      {course.seats_available}
                    </td>
                    <td className="px-4 py-4 text-center font-bold text-indigo-600">
                      {course.job_posting_volume}
                    </td>
                    <td className="px-4 py-4 text-center">
                      <span
                        className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-bold ${
                          isHigh
                            ? "bg-emerald-100 text-emerald-800"
                            : isLow
                            ? "bg-rose-100 text-rose-800"
                            : "bg-slate-100 text-slate-700"
                        }`}
                      >
                        {course.ratio}x
                      </span>
                    </td>
                    <td className="px-5 py-4 text-xs">
                      <span
                        className={`inline-flex items-center gap-1.5 font-medium ${
                          isHigh
                            ? "text-emerald-700"
                            : isLow
                            ? "text-rose-700"
                            : "text-slate-600"
                        }`}
                      >
                        {isHigh && <TrendingUp className="h-3.5 w-3.5 shrink-0" />}
                        {course.recommendation}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
