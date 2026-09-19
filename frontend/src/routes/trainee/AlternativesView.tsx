import { useEffect, useState } from "react";
import { api } from "../../lib/api";
import {
  ArrowLeft,
  Sparkles,
  Users,
  Compass,
  CheckCircle2,
} from "lucide-react";

export interface CourseAlternative {
  id: string;
  institute_id: string;
  institute_name: string;
  trade_id: string;
  trade_name: string;
  nsqf_code: string;
  seats_available: number;
  status: "active" | "flagged" | "obsolete";
  demand_label: string;
  recommendation_rationale: string;
}

export interface AlternativesGuide {
  flagged_course_name: string;
  flagged_institute_name: string;
  guidance_message: string;
  alternatives: CourseAlternative[];
}

interface AlternativesViewProps {
  courseId: string;
  onBack: () => void;
}

export function AlternativesView({ courseId, onBack }: AlternativesViewProps) {
  const [guide, setGuide] = useState<AlternativesGuide | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchAlternatives = async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await api<AlternativesGuide>(
          `/trainee/courses/${courseId}/alternatives`
        );
        setGuide(data);
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : "Failed to load alternatives");
      } finally {
        setLoading(false);
      }
    };

    fetchAlternatives();
  }, [courseId]);

  return (
    <div className="space-y-6">
      {/* Back button navigation */}
      <button
        onClick={onBack}
        className="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 shadow-sm hover:bg-slate-50 transition-colors"
      >
        <ArrowLeft className="h-4 w-4 text-slate-500" />
        Back to Course Catalog
      </button>

      {/* Loading state */}
      {loading && (
        <div className="space-y-4">
          <div className="h-32 animate-pulse rounded-2xl bg-amber-50/50 border border-amber-200" />
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="h-48 animate-pulse rounded-xl bg-slate-100 border border-slate-200" />
            <div className="h-48 animate-pulse rounded-xl bg-slate-100 border border-slate-200" />
          </div>
        </div>
      )}

      {/* Error state */}
      {error && (
        <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {error}
        </div>
      )}

      {/* Main Content */}
      {!loading && guide && (
        <div className="space-y-6">
          {/* Empathetic Career Guidance Hero Banner */}
          <div
            data-testid="guidance-card"
            className="rounded-2xl border border-amber-200 bg-gradient-to-br from-amber-50 via-orange-50/30 to-amber-50/50 p-6 shadow-sm"
          >
            <div className="flex items-start gap-4">
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-amber-600 text-white shadow-md shadow-amber-200">
                <Compass className="h-5 w-5" />
              </div>
              <div className="space-y-2">
                <div className="inline-flex items-center gap-2 rounded-full border border-amber-300 bg-amber-100/70 px-2.5 py-0.5 text-xs font-semibold text-amber-900">
                  Career Alignment Guidance
                </div>
                <h2 className="text-lg font-bold text-slate-900 sm:text-xl">
                  Modernizing Your Skilling Pathway for {guide.flagged_course_name}
                </h2>
                <p className="text-sm leading-relaxed text-slate-700">
                  {guide.guidance_message}
                </p>
                <div className="pt-2 text-xs font-medium text-slate-500">
                  Selected Course: <span className="font-semibold text-slate-700">{guide.flagged_course_name}</span> at {guide.flagged_institute_name}
                </div>
              </div>
            </div>
          </div>

          {/* Recommended Alternatives Section */}
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-bold text-slate-900 sm:text-lg">
                Recommended Active Courses in Your District ({guide.alternatives.length})
              </h3>
              <span className="text-xs text-slate-500">Ranked by industry hiring alignment</span>
            </div>

            {guide.alternatives.length === 0 ? (
              <div className="rounded-xl border border-slate-200 bg-white p-8 text-center text-sm text-slate-500">
                No alternative courses currently registered in this district. Consult with your local ITI guidance cell.
              </div>
            ) : (
              <div className="grid gap-4 sm:grid-cols-2">
                {guide.alternatives.map((alt) => (
                  <div
                    key={alt.id}
                    data-testid={`alt-card-${alt.id}`}
                    className="flex flex-col justify-between rounded-xl border border-emerald-200 bg-white p-5 shadow-sm hover:shadow-md transition-shadow"
                  >
                    <div>
                      <div className="flex items-center justify-between gap-2">
                        <span className="inline-flex items-center gap-1 rounded-full border border-emerald-200 bg-emerald-50 px-2.5 py-0.5 text-xs font-semibold text-emerald-700">
                          <Sparkles className="h-3 w-3" />
                          {alt.demand_label}
                        </span>
                        <span className="rounded bg-slate-100 px-2 py-0.5 font-mono text-xs text-slate-700">
                          {alt.nsqf_code}
                        </span>
                      </div>

                      <h4 className="mt-3 text-lg font-bold text-slate-900">
                        {alt.trade_name}
                      </h4>
                      <p className="mt-1 text-xs font-medium text-slate-600">
                        {alt.institute_name}
                      </p>

                      {/* Rationale Callout */}
                      <div className="mt-3 rounded-lg border border-slate-100 bg-slate-50 p-3 text-xs text-slate-600">
                        <div className="flex items-start gap-1.5">
                          <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-600 mt-0.5" />
                          <span className="leading-relaxed">{alt.recommendation_rationale}</span>
                        </div>
                      </div>
                    </div>

                    <div className="mt-4 flex items-center justify-between border-t border-slate-100 pt-3 text-xs text-slate-500">
                      <span className="flex items-center gap-1 font-medium text-slate-700">
                        <Users className="h-3.5 w-3.5 text-slate-400" />
                        {alt.seats_available} open seats
                      </span>
                      <span className="font-semibold text-emerald-700">
                        Active & Enrolling
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
