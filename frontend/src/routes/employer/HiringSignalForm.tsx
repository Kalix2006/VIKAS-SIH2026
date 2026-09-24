import { useState, useEffect } from "react";
import { Send, Check, AlertCircle, RefreshCw, Briefcase, Calendar, TrendingUp } from "lucide-react";
import { api } from "../../lib/api";
import { useAuth } from "../../lib/auth";

interface TradeOption {
  id: string;
  name: string;
  nsqf_code: string;
}

interface HiringSignalResponse {
  signal_id: string;
  trade_name: string;
  district_name: string;
  vacancies_count: number;
  timeframe_months: number;
  urgency: string;
  notes?: string;
  recorded_at: string;
}

export function HiringSignalForm() {
  const { user } = useAuth();
  const [trades, setTrades] = useState<TradeOption[]>([]);
  const [selectedTradeId, setSelectedTradeId] = useState<string>("");
  const [vacancies, setVacancies] = useState<number>(25);
  const [timeframe, setTimeframe] = useState<number>(3);
  const [urgency, setUrgency] = useState<string>("immediate");
  const [notes, setNotes] = useState<string>("");
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [result, setResult] = useState<HiringSignalResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadTrades() {
      try {
        const res = await api<any[]>("/trainee/courses?district_id=" + (user?.district_id || ""));
        if (Array.isArray(res)) {
          const uniqueTrades = Array.from(
            new Map(res.map((c) => [c.trade_id, { id: c.trade_id, name: c.trade_name, nsqf_code: c.nsqf_code }])).values()
          );
          setTrades(uniqueTrades as TradeOption[]);
          if (uniqueTrades.length > 0 && uniqueTrades[0]) {
            setSelectedTradeId((uniqueTrades[0] as TradeOption).id);
          }
        }
      } catch {
        const fallbackTrades: TradeOption[] = [
          { id: "548294f7-6e6d-4e5c-a8e9-731096bcba67", name: "Electrician", nsqf_code: "NSQF-L4-ELE" },
          { id: "650e0bf3-0428-4446-a225-74b70f7fe163", name: "Fitter", nsqf_code: "NSQF-L4-FIT" },
          { id: "74de65d3-982b-4461-b37c-62a46962e879", name: "Welder", nsqf_code: "NSQF-L4-WLD" },
          { id: "21347113-824f-47a8-9019-6626c6b5a472", name: "Automobile/Diesel Mechanic", nsqf_code: "NSQF-L4-ADM" },
          { id: "d158509c-0121-49c8-9b34-2e163a850794", name: "COPA", nsqf_code: "NSQF-L4-COP" },
        ];
        setTrades(fallbackTrades);
        if (fallbackTrades[0]) {
          setSelectedTradeId(fallbackTrades[0].id);
        }
      }
    }
    loadTrades();
  }, [user?.district_id]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedTradeId || vacancies <= 0) {
      setError("Please specify a valid trade and vacancy count.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const payload = {
        trade_id: selectedTradeId,
        district_id: user?.district_id,
        vacancies_count: vacancies,
        timeframe_months: timeframe,
        urgency,
        notes: notes.trim() || undefined,
      };
      const res = await api<HiringSignalResponse>("/employer/hiring-signal", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      setResult(res);
    } catch (err: any) {
      setError(err.message || "Failed to record hiring signal");
    } finally {
      setSubmitting(false);
    }
  };

  const vacancyPresets = [5, 15, 25, 50, 100];
  const timeframeOptions = [
    { months: 1, label: "Next 30 Days (Immediate)" },
    { months: 3, label: "Next 3 Months (Quarterly Target)" },
    { months: 6, label: "Next 6 Months (Expansion Phase)" },
    { months: 12, label: "Next 12 Months (Annual Plan)" },
  ];

  return (
    <div className="space-y-6 max-w-2xl">
      <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm space-y-6">
        <div>
          <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
            <Briefcase className="h-5 w-5 text-blue-600" />
            Signal Upcoming Hiring Intentions
          </h2>
          <p className="text-xs text-slate-500 mt-1">
            Submit your upcoming vacancy projections. District planners use this data to adjust ITI intake quotas and trainer refresher programs before shortages hit.
          </p>
        </div>

        {error && (
          <div className="flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
            <AlertCircle className="h-4 w-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {result && (
          <div className="rounded-xl border border-emerald-200 bg-emerald-50/80 p-5 shadow-sm space-y-2">
            <div className="flex items-center gap-2 text-emerald-800 font-bold text-sm">
              <Check className="h-5 w-5 rounded-full bg-emerald-600 text-white p-0.5" />
              Hiring Signal Recorded Successfully!
            </div>
            <p className="text-xs text-emerald-700">
              Registered intent for <span className="font-semibold">{result.vacancies_count} {result.trade_name}</span> openings in {result.district_name} across the next {result.timeframe_months} months.
            </p>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-5">
          {/* Target Trade */}
          <div>
            <label className="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-1.5">
              Vocational Trade
            </label>
            <select
              value={selectedTradeId}
              onChange={(e) => setSelectedTradeId(e.target.value)}
              className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-800 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            >
              {trades.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.name} ({t.nsqf_code})
                </option>
              ))}
            </select>
          </div>

          {/* Vacancies Volume */}
          <div>
            <label className="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-1.5">
              Projected Vacancy Volume
            </label>
            <div className="flex items-center gap-2 mb-2">
              {vacancyPresets.map((preset) => (
                <button
                  key={preset}
                  type="button"
                  onClick={() => setVacancies(preset)}
                  className={`rounded-lg px-3 py-1 text-xs font-bold transition-colors ${
                    vacancies === preset
                      ? "bg-blue-600 text-white shadow-sm"
                      : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                  }`}
                >
                  +{preset}
                </button>
              ))}
            </div>
            <input
              type="number"
              min={1}
              max={1000}
              value={vacancies}
              onChange={(e) => setVacancies(parseInt(e.target.value) || 0)}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>

          {/* Timeframe */}
          <div>
            <label className="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-1.5 flex items-center gap-1">
              <Calendar className="h-3.5 w-3.5 text-slate-500" />
              Target Hiring Timeframe
            </label>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {timeframeOptions.map((opt) => (
                <button
                  key={opt.months}
                  type="button"
                  onClick={() => setTimeframe(opt.months)}
                  className={`rounded-lg border p-2.5 text-left text-xs font-medium transition-all ${
                    timeframe === opt.months
                      ? "border-blue-600 bg-blue-50/70 text-blue-900 font-semibold"
                      : "border-slate-200 bg-white text-slate-700 hover:border-slate-300"
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>

          {/* Urgency Category */}
          <div>
            <label className="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-1.5 flex items-center gap-1">
              <TrendingUp className="h-3.5 w-3.5 text-slate-500" />
              Urgency Type
            </label>
            <div className="grid grid-cols-3 gap-2">
              {[
                { id: "immediate", label: "Immediate Hiring" },
                { id: "upcoming", label: "Pipeline Building" },
                { id: "apprenticeship", label: "Apprenticeship" },
              ].map((u) => (
                <button
                  key={u.id}
                  type="button"
                  onClick={() => setUrgency(u.id)}
                  className={`rounded-lg border p-2 text-center text-xs font-medium transition-all ${
                    urgency === u.id
                      ? "border-blue-600 bg-blue-600 text-white font-semibold shadow-sm"
                      : "border-slate-200 bg-white text-slate-700 hover:bg-slate-50"
                  }`}
                >
                  {u.label}
                </button>
              ))}
            </div>
          </div>

          {/* Optional Notes */}
          <div>
            <label className="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-1.5">
              Specific Tooling or Shift Requirements (Optional)
            </label>
            <textarea
              rows={3}
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="e.g. Willing to conduct on-campus placement for trainees with heavy machinery certificate..."
              className="w-full rounded-lg border border-slate-300 p-2.5 text-xs shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>

          <button
            type="submit"
            disabled={submitting}
            className="flex w-full items-center justify-center gap-2 rounded-xl bg-blue-600 py-3 text-sm font-bold text-white shadow-md shadow-blue-200 hover:bg-blue-700 transition-all disabled:opacity-50"
          >
            {submitting ? (
              <>
                <RefreshCw className="h-4 w-4 animate-spin" />
                Recording Signal...
              </>
            ) : (
              <>
                <Send className="h-4 w-4" />
                Record Hiring Demand Intent
              </>
            )}
          </button>
        </form>
      </div>
    </div>
  );
}
