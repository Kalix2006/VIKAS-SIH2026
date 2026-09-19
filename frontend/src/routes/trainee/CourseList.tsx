import { useEffect, useState } from "react";
import { api } from "../../lib/api";
import {
  GraduationCap,
  Users,
  AlertTriangle,
  ArrowRight,
  Sparkles,
  RefreshCw,
  Search,
} from "lucide-react";

export interface TraineeCourse {
  id: string;
  institute_id: string;
  institute_name: string;
  trade_id: string;
  trade_name: string;
  nsqf_code: string;
  seats_available: number;
  status: "active" | "flagged" | "obsolete";
  demand_label: string;
  demand_level: "high" | "stable" | "caution" | "emerging";
  has_alternatives: boolean;
}

interface CourseListProps {
  onSelectCourseAlternatives?: (courseId: string) => void;
}

export function CourseList({ onSelectCourseAlternatives }: CourseListProps) {
  const [courses, setCourses] = useState<TraineeCourse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState<"all" | "active" | "flagged">("all");

  const fetchCourses = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api<TraineeCourse[]>("/trainee/courses");
      setCourses(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load courses");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCourses();
  }, []);

  const filteredCourses = courses.filter((c) => {
    const matchesSearch =
      c.trade_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      c.institute_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      c.nsqf_code.toLowerCase().includes(searchTerm.toLowerCase());

    const matchesStatus =
      statusFilter === "all" ||
      (statusFilter === "active" && c.status === "active") ||
      (statusFilter === "flagged" && (c.status === "flagged" || c.status === "obsolete"));

    return matchesSearch && matchesStatus;
  });

  const getDemandBadgeClass = (level: string) => {
    switch (level) {
      case "high":
        return "bg-emerald-50 text-emerald-700 border-emerald-200";
      case "caution":
        return "bg-amber-50 text-amber-800 border-amber-200";
      case "emerging":
        return "bg-purple-50 text-purple-700 border-purple-200";
      default:
        return "bg-blue-50 text-blue-700 border-blue-200";
    }
  };

  return (
    <div className="space-y-6">
      {/* Header & Controls */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-xl font-bold tracking-tight text-slate-900 sm:text-2xl">
            District Vocational Courses
          </h2>
          <p className="mt-1 text-sm text-slate-500">
            Explore accredited courses in your district with employer demand signals
          </p>
        </div>

        <button
          onClick={fetchCourses}
          disabled={loading}
          className="inline-flex items-center gap-2 self-start rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 shadow-sm hover:bg-slate-50 disabled:opacity-50"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
          Refresh
        </button>
      </div>

      {/* Filter and Search Bar */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
          <input
            type="text"
            placeholder="Search trade, institute, or NSQF code..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full rounded-lg border border-slate-300 py-2 pl-9 pr-3 text-sm focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500"
          />
        </div>

        <div className="flex gap-2">
          {(["all", "active", "flagged"] as const).map((filter) => (
            <button
              key={filter}
              onClick={() => setStatusFilter(filter)}
              className={`rounded-lg px-3 py-1.5 text-xs font-medium capitalize transition-colors ${
                statusFilter === filter
                  ? "bg-slate-900 text-white"
                  : "bg-slate-100 text-slate-600 hover:bg-slate-200"
              }`}
            >
              {filter}
            </button>
          ))}
        </div>
      </div>

      {/* Error state */}
      {error && (
        <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {error}
        </div>
      )}

      {/* Loading skeleton */}
      {loading && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {[1, 2, 3, 4, 5, 6].map((n) => (
            <div
              key={n}
              className="h-44 animate-pulse rounded-xl border border-slate-200 bg-slate-100 p-5"
            />
          ))}
        </div>
      )}

      {/* Empty State */}
      {!loading && filteredCourses.length === 0 && (
        <div className="rounded-2xl border border-dashed border-slate-300 bg-slate-50/50 p-12 text-center">
          <GraduationCap className="mx-auto h-10 w-10 text-slate-400" />
          <h3 className="mt-3 text-sm font-semibold text-slate-800">No courses match your criteria</h3>
          <p className="mt-1 text-xs text-slate-500">Try adjusting your search query or filters.</p>
        </div>
      )}

      {/* Course Cards Grid */}
      {!loading && filteredCourses.length > 0 && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {filteredCourses.map((course) => {
            const isFlagged = course.status === "flagged" || course.status === "obsolete";

            return (
              <div
                key={course.id}
                data-testid={`course-card-${course.id}`}
                className={`relative flex flex-col justify-between rounded-xl border p-5 shadow-sm transition-all hover:shadow-md ${
                  isFlagged
                    ? "border-amber-200 bg-gradient-to-b from-amber-50/40 to-white"
                    : "border-slate-200 bg-white"
                }`}
              >
                <div>
                  {/* Status & Demand Badges */}
                  <div className="flex flex-wrap items-center gap-2">
                    <span
                      data-testid="demand-badge"
                      className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs font-semibold ${getDemandBadgeClass(
                        course.demand_level
                      )}`}
                    >
                      <Sparkles className="h-3 w-3" />
                      {course.demand_label}
                    </span>

                    {isFlagged && (
                      <span
                        data-testid="flagged-badge"
                        className="inline-flex items-center gap-1 rounded-full border border-amber-300 bg-amber-100 px-2.5 py-0.5 text-xs font-medium text-amber-800"
                      >
                        <AlertTriangle className="h-3 w-3" />
                        Modernization Advisory
                      </span>
                    )}
                  </div>

                  {/* Trade Title */}
                  <h3 className="mt-3 text-lg font-bold tracking-tight text-slate-900">
                    {course.trade_name}
                  </h3>

                  {/* Institute & NSQF */}
                  <p className="mt-1 text-xs font-medium text-slate-600">
                    {course.institute_name}
                  </p>

                  <div className="mt-3 flex items-center gap-4 text-xs text-slate-500">
                    <span className="rounded bg-slate-100 px-2 py-0.5 font-mono text-slate-700">
                      NSQF: {course.nsqf_code}
                    </span>
                    <span className="flex items-center gap-1">
                      <Users className="h-3.5 w-3.5 text-slate-400" />
                      {course.seats_available} open seats
                    </span>
                  </div>
                </div>

                {/* Footer action */}
                <div className="mt-5 pt-3 border-t border-slate-100">
                  {isFlagged ? (
                    <button
                      data-testid="view-alternatives-btn"
                      onClick={() => onSelectCourseAlternatives?.(course.id)}
                      className="flex w-full items-center justify-center gap-1.5 rounded-lg bg-amber-600 px-3 py-2 text-xs font-semibold text-white shadow-sm hover:bg-amber-700 transition-colors"
                    >
                      <span>View Recommended Alternatives</span>
                      <ArrowRight className="h-3.5 w-3.5" />
                    </button>
                  ) : (
                    <div className="flex items-center justify-between text-xs text-slate-500">
                      <span className="inline-flex items-center gap-1 text-emerald-700 font-medium">
                        <span className="h-2 w-2 rounded-full bg-emerald-500" />
                        Direct Enrollment Open
                      </span>
                      <span className="text-slate-400">At Center</span>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

