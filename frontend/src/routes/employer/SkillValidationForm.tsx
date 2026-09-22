import { useState, useEffect } from "react";
import { Check, Plus, Sparkles, Clock, AlertCircle, RefreshCw, ChevronDown, ChevronUp } from "lucide-react";
import { api } from "../../lib/api";
import { useAuth } from "../../lib/auth";

interface InferredSkill {
  skill_name: string;
  category: string;
  posting_frequency: number;
  is_recommended: boolean;
}

interface InferredSkillsResponse {
  trade_id: string;
  trade_name: string;
  nsqf_code: string;
  district_id: string;
  district_name: string;
  total_postings_analyzed: number;
  inferred_skills: InferredSkill[];
}

interface ValidationResponse {
  validation_id: string;
  trade_name: string;
  district_name: string;
  confirmed_skills: string[];
  extracted_from_free_text: string[];
  parsed_by_llm: boolean;
  needs_manual_review: boolean;
  submitted_at: string;
}

interface TradeOption {
  id: string;
  name: string;
  nsqf_code: string;
}

export function SkillValidationForm() {
  const { user } = useAuth();
  const [trades, setTrades] = useState<TradeOption[]>([]);
  const [selectedTradeId, setSelectedTradeId] = useState<string>("");
  const [inferredData, setInferredData] = useState<InferredSkillsResponse | null>(null);
  const [selectedSkills, setSelectedSkills] = useState<Set<string>>(new Set());
  const [customAddedSkills, setCustomAddedSkills] = useState<string[]>([]);
  const [customSkill, setCustomSkill] = useState("");
  const [rawText, setRawText] = useState("");
  const [showRawText, setShowRawText] = useState(false);
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<ValidationResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Load trades list on mount
  useEffect(() => {
    async function loadTrades() {
      try {
        // Fetch planner map or trade expectations to get trades list
        const res = await api<{ trades?: TradeOption[] } | TradeOption[]>("/trainee/courses?district_id=" + (user?.district_id || ""));
        if (Array.isArray(res)) {
          const uniqueTrades = Array.from(new Map(res.map((c: any) => [c.trade_id, { id: c.trade_id, name: c.trade_name, nsqf_code: c.nsqf_code }])).values());
          setTrades(uniqueTrades as TradeOption[]);
          if (uniqueTrades.length > 0 && uniqueTrades[0]) {
            setSelectedTradeId((uniqueTrades[0] as TradeOption).id);
          }
        }
      } catch {
        // Fallback standard trades
        const fallbackTrades: TradeOption[] = [
          { id: "548294f7-6e6d-4e5c-a8e9-731096bcba67", name: "Electrician", nsqf_code: "NSQF-L4-ELE" },
          { id: "650e0bf3-0428-4446-a225-74b70f7fe163", name: "Fitter", nsqf_code: "NSQF-L4-FIT" },
          { id: "74de65d3-982b-4461-b37c-62a46962e879", name: "Welder", nsqf_code: "NSQF-L4-WLD" },
          { id: "a4000000-0000-0000-0000-000000000004", name: "Automobile/Diesel Mechanic", nsqf_code: "MEC/Q0101" },
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

  // Load inferred skills whenever selectedTradeId changes
  useEffect(() => {
    if (!selectedTradeId || !user?.district_id) return;
    async function loadInferredSkills() {
      setLoading(true);
      setError(null);
      setResult(null);
      try {
        const data = await api<InferredSkillsResponse>(
          `/employer/skills-inferred?trade_id=${selectedTradeId}&district_id=${user?.district_id}`
        );
        setInferredData(data);
        // Pre-select all inferred skills by default for ultra-low friction confirmation
        const allSkillNames = new Set(data.inferred_skills.map((s) => s.skill_name));
        setSelectedSkills(allSkillNames);
      } catch (err: any) {
        setError(err.message || "Failed to load inferred skills");
      } finally {
        setLoading(false);
      }
    }
    loadInferredSkills();
  }, [selectedTradeId, user?.district_id]);

  const toggleSkill = (skillName: string) => {
    setSelectedSkills((prev) => {
      const next = new Set(prev);
      if (next.has(skillName)) {
        next.delete(skillName);
      } else {
        next.add(skillName);
      }
      return next;
    });
  };

  const handleSelectAll = () => {
    if (!inferredData) return;
    setSelectedSkills(new Set(inferredData.inferred_skills.map((s) => s.skill_name)));
  };

  const handleClearAll = () => {
    setSelectedSkills(new Set());
  };

  const handleAddCustomSkill = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = customSkill.trim();
    if (!trimmed) return;
    if (!customAddedSkills.includes(trimmed)) {
      setCustomAddedSkills((prev) => [...prev, trimmed]);
    }
    setSelectedSkills((prev) => new Set([...prev, trimmed]));
    setCustomSkill("");
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (selectedSkills.size === 0 && !rawText.trim()) {
      setError("Please select at least one skill or provide requirements in free text.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const payload = {
        trade_id: selectedTradeId,
        district_id: user?.district_id,
        confirmed_skills: Array.from(selectedSkills),
        raw_free_text: rawText.trim() || undefined,
      };
      const res = await api<ValidationResponse>("/employer/validate", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      setResult(res);
    } catch (err: any) {
      setError(err.message || "Failed to submit skill validation");
    } finally {
      setSubmitting(false);
    }
  };

  const categories = [
    { key: "core_tool", label: "Core Tools & Machinery", color: "border-blue-200 bg-blue-50/50 text-blue-900" },
    { key: "technical_competency", label: "Technical Competencies", color: "border-indigo-200 bg-indigo-50/50 text-indigo-900" },
    { key: "emerging", label: "Emerging & Modern Tech", color: "border-emerald-200 bg-emerald-50/50 text-emerald-900" },
  ];

  return (
    <div className="space-y-6">
      {/* Top Banner: Low friction speed promise */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 rounded-xl border border-blue-200 bg-gradient-to-r from-blue-50 via-sky-50 to-indigo-50 p-4 shadow-sm">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-600 text-white shadow-sm">
            <Clock className="h-5 w-5" />
          </div>
          <div>
            <h2 className="text-sm font-bold text-slate-900">
              One-Minute Industrial Skill Confirmation
            </h2>
            <p className="text-xs text-slate-600">
              Pre-filled from recent local vacancies. Toggle what you need, add custom tools, and submit instantly.
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2 self-end sm:self-auto rounded-full bg-white/90 px-3 py-1 text-xs font-semibold text-blue-700 border border-blue-200 shadow-sm">
          <Sparkles className="h-3.5 w-3.5 text-blue-600 animate-pulse" />
          Average Completion: 25 seconds
        </div>
      </div>

      {/* Trade Selector & Quick Actions */}
      <div className="flex flex-wrap items-center justify-between gap-4 bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
        <div className="flex items-center gap-3">
          <label className="text-xs font-bold uppercase tracking-wider text-slate-600">
            Target Trade:
          </label>
          <select
            value={selectedTradeId}
            onChange={(e) => setSelectedTradeId(e.target.value)}
            className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm font-semibold text-slate-800 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          >
            {trades.map((t) => (
              <option key={t.id} value={t.id}>
                {t.name} ({t.nsqf_code})
              </option>
            ))}
          </select>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={handleSelectAll}
            className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-100 transition-colors"
          >
            Select All
          </button>
          <button
            type="button"
            onClick={handleClearAll}
            className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-100 transition-colors"
          >
            Deselect All
          </button>
        </div>
      </div>

      {error && (
        <div className="flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
          <AlertCircle className="h-4 w-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Confirmation Success Card */}
      {result && (
        <div className="rounded-xl border border-emerald-200 bg-emerald-50/80 p-5 shadow-sm space-y-3">
          <div className="flex items-center gap-2 text-emerald-800 font-bold text-sm">
            <Check className="h-5 w-5 rounded-full bg-emerald-600 text-white p-0.5" />
            Skill Validation Confirmed for {result.trade_name} ({result.district_name})!
          </div>
          <p className="text-xs text-emerald-700">
            Recorded {result.confirmed_skills.length} confirmed competencies. Your requirements directly calibrate the district curriculum alignment index.
          </p>
          {result.extracted_from_free_text.length > 0 && (
            <div data-testid="free-text-extracted" className="mt-2 pt-2 border-t border-emerald-200/60 text-xs text-emerald-800">
              <span className="font-semibold">Extracted from Free-Text ({result.parsed_by_llm ? "Groq AI" : "Rule-Based"}): </span>
              <span data-testid="extracted-skill-list">{result.extracted_from_free_text.join(", ")}</span>
            </div>
          )}
          {result.needs_manual_review && (
            <div className="text-[11px] text-amber-700 font-medium">
              Note: Free-text was flagged for supervisory verification.
            </div>
          )}
        </div>
      )}

      {/* Interactive Chip Groups */}
      {loading ? (
        <div className="flex h-48 items-center justify-center rounded-xl border border-slate-200 bg-white">
          <div className="flex items-center gap-2 text-sm text-slate-500">
            <RefreshCw className="h-4 w-4 animate-spin text-blue-600" />
            Analyzing local vacancy postings & NSQF standards...
          </div>
        </div>
      ) : inferredData ? (
        <form onSubmit={handleSubmit} className="space-y-6">
          {categories.map((cat) => {
            const items = inferredData.inferred_skills.filter(
              (s) => s.category === cat.key || (cat.key === "technical_competency" && !["core_tool", "emerging"].includes(s.category))
            );
            if (items.length === 0) return null;

            return (
              <div key={cat.key} className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm space-y-3">
                <div className="flex items-center justify-between">
                  <h3 className="text-xs font-bold uppercase tracking-wider text-slate-700">
                    {cat.label}
                  </h3>
                  <span className="text-[11px] text-slate-400">
                    {items.filter((i) => selectedSkills.has(i.skill_name)).length} of {items.length} confirmed
                  </span>
                </div>

                <div className="flex flex-wrap gap-2 pt-1">
                  {items.map((skill) => {
                    const isSelected = selectedSkills.has(skill.skill_name);
                    return (
                      <button
                        key={skill.skill_name}
                        type="button"
                        onClick={() => toggleSkill(skill.skill_name)}
                        className={`flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-xs font-medium transition-all ${
                          isSelected
                            ? "border-blue-600 bg-blue-600 text-white shadow-sm"
                            : "border-slate-200 bg-slate-50 text-slate-700 hover:border-slate-300 hover:bg-slate-100"
                        }`}
                      >
                        <div
                          className={`flex h-3.5 w-3.5 items-center justify-center rounded ${
                            isSelected ? "bg-white text-blue-600" : "border border-slate-400 bg-white"
                          }`}
                        >
                          {isSelected && <Check className="h-2.5 w-2.5 stroke-[3]" />}
                        </div>
                        <span>{skill.skill_name}</span>
                        {skill.posting_frequency > 1 && (
                          <span
                            className={`rounded-full px-1.5 py-0.2 text-[10px] ${
                              isSelected ? "bg-blue-700 text-blue-100" : "bg-slate-200 text-slate-600"
                            }`}
                          >
                            {skill.posting_frequency}x
                          </span>
                        )}
                      </button>
                    );
                  })}
                  </div>
                </div>
              );
            })}

          {customAddedSkills.length > 0 && (
            <div className="rounded-xl border border-purple-200 bg-purple-50/40 p-5 shadow-sm space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="text-xs font-bold uppercase tracking-wider text-purple-900">
                  Custom Employer Additions
                </h3>
                <span className="text-[11px] text-purple-600">
                  {customAddedSkills.filter((s) => selectedSkills.has(s)).length} confirmed
                </span>
              </div>
              <div className="flex flex-wrap gap-2 pt-1">
                {customAddedSkills.map((skill) => {
                  const isSelected = selectedSkills.has(skill);
                  return (
                    <button
                      key={skill}
                      type="button"
                      onClick={() => toggleSkill(skill)}
                      className={`flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-xs font-medium transition-all ${
                        isSelected
                          ? "border-purple-600 bg-purple-600 text-white shadow-sm"
                          : "border-slate-200 bg-white text-slate-700 hover:border-slate-300"
                      }`}
                    >
                      <div
                        className={`flex h-3.5 w-3.5 items-center justify-center rounded ${
                          isSelected ? "bg-white text-purple-600" : "border border-slate-400 bg-white"
                        }`}
                      >
                        {isSelected && <Check className="h-2.5 w-2.5 stroke-[3]" />}
                      </div>
                      <span>{skill}</span>
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {/* Quick-Add Custom Skill */}
          <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2">
              <input
                type="text"
                value={customSkill}
                onChange={(e) => setCustomSkill(e.target.value)}
                placeholder="Missing a specific tool/skill? (e.g. CNC Five-Axis Setup, ABB Robotics)"
                className="flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
              <button
                type="button"
                onClick={handleAddCustomSkill}
                className="flex items-center justify-center gap-1 rounded-lg border border-slate-300 bg-slate-100 px-4 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-200 transition-colors"
              >
                <Plus className="h-4 w-4" />
                Add Skill
              </button>
            </div>
          </div>

          {/* Optional Accordion: Free Text Box with Groq Parser */}
          <div className="rounded-xl border border-slate-200 bg-white shadow-sm overflow-hidden">
            <button
              type="button"
              onClick={() => setShowRawText(!showRawText)}
              className="flex w-full items-center justify-between p-4 text-left text-xs font-bold uppercase tracking-wider text-slate-700 hover:bg-slate-50 transition-colors"
            >
              <div className="flex items-center gap-2">
                <Sparkles className="h-4 w-4 text-purple-600" />
                <span>Have a Job Description or Free-Text Requirements? (Optional AI Extraction)</span>
              </div>
              {showRawText ? <ChevronUp className="h-4 w-4 text-slate-400" /> : <ChevronDown className="h-4 w-4 text-slate-400" />}
            </button>

            {showRawText && (
              <div className="p-4 pt-0 space-y-2 border-t border-slate-100">
                <p className="text-xs text-slate-500">
                  Paste raw vacancy descriptions, tool lists, or syllabus suggestions. Our Groq parser will extract competencies automatically.
                </p>
                <textarea
                  rows={4}
                  value={rawText}
                  onChange={(e) => setRawText(e.target.value)}
                  placeholder="e.g. We are expanding our Pune electric powertrain line. Candidates must know high-voltage insulation testing, CAN-bus logging, and motor stator winding..."
                  className="w-full rounded-lg border border-slate-300 p-3 text-xs shadow-sm focus:border-purple-500 focus:outline-none focus:ring-1 focus:ring-purple-500"
                />
              </div>
            )}
          </div>

          {/* Action Bar */}
          <div className="flex flex-col sm:flex-row items-center justify-between gap-3 pt-2">
            <div className="text-xs text-slate-500">
              <span className="font-bold text-slate-800">{selectedSkills.size} skills</span> selected for confirmation
            </div>
            <button
              type="submit"
              disabled={submitting || (selectedSkills.size === 0 && !rawText.trim())}
              className="flex w-full sm:w-auto items-center justify-center gap-2 rounded-xl bg-blue-600 px-6 py-3 text-sm font-bold text-white shadow-md shadow-blue-200 hover:bg-blue-700 transition-all disabled:opacity-50"
            >
              {submitting ? (
                <>
                  <RefreshCw className="h-4 w-4 animate-spin" />
                  Recording Skill Validation...
                </>
              ) : (
                <>
                  <Check className="h-4 w-4" />
                  Confirm & Submit Skill Demand
                </>
              )}
            </button>
          </div>
        </form>
      ) : null}
    </div>
  );
}
