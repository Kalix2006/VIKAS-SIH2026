import { useEffect, useState } from "react";
import { api } from "../../lib/api";
import { Bell, RefreshCw, CheckCircle2, Bot, FileText } from "lucide-react";

export interface TraineeAlert {
  id: string;
  message: string;
  generated_by: "template" | "groq";
  reviewed: boolean;
  created_at: string;
}

export function AlertsView() {
  const [alerts, setAlerts] = useState<TraineeAlert[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchAlerts = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api<TraineeAlert[]>("/trainee/alerts");
      setAlerts(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load alerts");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAlerts();
  }, []);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold tracking-tight text-slate-900 sm:text-2xl">
            Notifications & Career Advisories
          </h2>
          <p className="mt-1 text-sm text-slate-500">
            District updates on curriculum alignment and vocational opportunities
          </p>
        </div>

        <button
          onClick={fetchAlerts}
          disabled={loading}
          className="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 shadow-sm hover:bg-slate-50 disabled:opacity-50"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
          Refresh
        </button>
      </div>

      {error && (
        <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {error}
        </div>
      )}

      {loading && (
        <div className="space-y-3">
          {[1, 2, 3].map((n) => (
            <div key={n} className="h-24 animate-pulse rounded-xl bg-slate-100 border border-slate-200" />
          ))}
        </div>
      )}

      {!loading && alerts.length === 0 && (
        <div className="rounded-2xl border border-dashed border-slate-300 bg-slate-50/50 p-12 text-center">
          <CheckCircle2 className="mx-auto h-10 w-10 text-emerald-500" />
          <h3 className="mt-3 text-sm font-semibold text-slate-800">You are all caught up!</h3>
          <p className="mt-1 text-xs text-slate-500">No pending alerts or modernization notices for your profile.</p>
        </div>
      )}

      {!loading && alerts.length > 0 && (
        <div className="space-y-3">
          {alerts.map((alert) => (
            <div
              key={alert.id}
              className="flex items-start gap-4 rounded-xl border border-slate-200 bg-white p-4 shadow-sm hover:shadow-md transition-shadow"
            >
              <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-emerald-100 text-emerald-700">
                <Bell className="h-4 w-4" />
              </div>

              <div className="flex-1 space-y-1">
                <p className="text-sm font-medium leading-relaxed text-slate-800">
                  {alert.message}
                </p>
                <div className="flex items-center gap-3 text-[11px] text-slate-400">
                  <span>{new Date(alert.created_at).toLocaleDateString()}</span>
                  <span>•</span>
                  <span className="flex items-center gap-1">
                    {alert.generated_by === "groq" ? (
                      <>
                        <Bot className="h-3 w-3 text-purple-600" />
                        AI Phrased
                      </>
                    ) : (
                      <>
                        <FileText className="h-3 w-3 text-slate-500" />
                        Official Notice
                      </>
                    )}
                  </span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

