import React, { useState, useRef, useEffect } from "react";
import { api } from "../../lib/api";
import {
  Send,
  Sparkles,
  Bot,
  User,
  ShieldCheck,
  AlertCircle,
  Database,
} from "lucide-react";

interface Message {
  id: string;
  sender: "user" | "assistant";
  text: string;
  groundedDistrict?: string;
  coursesCount?: number;
  fallbackUsed?: boolean;
}

const SUGGESTED_QUESTIONS = [
  "What electrician courses are available in Pune?",
  "Are there active seats for COPA or welding in my district?",
  "What alternative courses can I consider if my trade is modernized?",
  "Which trades currently have strong local employer hiring?",
];

export function TraineeChat() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "welcome",
      sender: "assistant",
      text: "Namaste! I am your VIKAS AI Career Counselor. I can help you explore vocational courses, seats, syllabus modernization, and employer skill demands in your district.",
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  const handleSend = async (questionText?: string) => {
    const q = (questionText || input).trim();
    if (!q || loading) return;

    const userMessage: Message = {
      id: `user-${Date.now()}`,
      sender: "user",
      text: q,
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setError(null);
    setLoading(true);

    try {
      const response = await api<{
        reply: string;
        grounded_district: string;
        grounded_courses_count: number;
        fallback_used: boolean;
      }>("/trainee/chat", {
        method: "POST",
        body: JSON.stringify({ question: q }),
      });

      const botMessage: Message = {
        id: `bot-${Date.now()}`,
        sender: "assistant",
        text: response.reply,
        groundedDistrict: response.grounded_district,
        coursesCount: response.grounded_courses_count,
        fallbackUsed: response.fallback_used,
      };

      setMessages((prev) => [...prev, botMessage]);
    } catch (err: unknown) {
      setError(
        err instanceof Error ? err.message : "Unable to reach career assistant."
      );
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex flex-col h-[calc(100vh-14rem)] min-h-[480px] max-h-[720px] rounded-2xl border border-slate-200 bg-white shadow-sm overflow-hidden">
      {/* Top Grounding Notice Header */}
      <div className="flex items-center justify-between border-b border-slate-100 bg-slate-50/80 px-4 py-3">
        <div className="flex items-center gap-2">
          <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-emerald-600 text-white shadow-xs">
            <Bot className="h-4 w-4" />
          </div>
          <div>
            <h3 className="text-xs font-bold text-slate-800">
              VIKAS Grounded Career Counselor
            </h3>
            <p className="text-[11px] text-slate-500">
              Answers generated strictly from verified district skilling data
            </p>
          </div>
        </div>

        <div className="hidden sm:flex items-center gap-1.5 rounded-full border border-emerald-200 bg-emerald-50 px-2.5 py-1 text-[11px] font-medium text-emerald-800">
          <ShieldCheck className="h-3.5 w-3.5 text-emerald-600" />
          <span>Strictly Grounded</span>
        </div>
      </div>

      {/* Messages Thread */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((m) => (
          <div
            key={m.id}
            className={`flex items-start gap-2.5 ${
              m.sender === "user" ? "flex-row-reverse" : "flex-row"
            }`}
          >
            <div
              className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-xs font-semibold ${
                m.sender === "user"
                  ? "bg-emerald-600 text-white"
                  : "bg-slate-200 text-slate-700"
              }`}
            >
              {m.sender === "user" ? (
                <User className="h-4 w-4" />
              ) : (
                <Bot className="h-4 w-4 text-emerald-700" />
              )}
            </div>

            <div
              className={`max-w-[82%] rounded-2xl px-4 py-3 text-sm leading-relaxed shadow-xs ${
                m.sender === "user"
                  ? "bg-emerald-600 text-white rounded-tr-xs"
                  : "bg-slate-100/80 text-slate-800 rounded-tl-xs border border-slate-200/50"
              }`}
            >
              <p>{m.text}</p>

              {/* Grounding & Provenance Tag for Assistant */}
              {m.sender === "assistant" && m.groundedDistrict && (
                <div className="mt-2.5 pt-2 border-t border-slate-200/60 flex items-center justify-between text-[10px] text-slate-500">
                  <span className="flex items-center gap-1">
                    <Database className="h-3 w-3 text-slate-400" />
                    Grounded in {m.groundedDistrict} ({m.coursesCount} courses)
                  </span>
                  {m.fallbackUsed && (
                    <span className="rounded bg-amber-50 px-1.5 py-0.5 text-amber-700 font-medium border border-amber-200">
                      Standard Template
                    </span>
                  )}
                </div>
              )}
            </div>
          </div>
        ))}

        {/* Loading Bubble */}
        {loading && (
          <div className="flex items-start gap-2.5">
            <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-slate-200 text-slate-700">
              <Bot className="h-4 w-4 text-emerald-700" />
            </div>
            <div className="rounded-2xl rounded-tl-xs bg-slate-100/80 px-4 py-3 border border-slate-200/50">
              <div className="flex items-center gap-2 text-xs text-slate-500">
                <div className="flex gap-1">
                  <div className="h-2 w-2 animate-bounce rounded-full bg-emerald-600 [animation-delay:-0.3s]" />
                  <div className="h-2 w-2 animate-bounce rounded-full bg-emerald-600 [animation-delay:-0.15s]" />
                  <div className="h-2 w-2 animate-bounce rounded-full bg-emerald-600" />
                </div>
                <span>Checking verified district courses...</span>
              </div>
            </div>
          </div>
        )}

        {/* Error notification */}
        {error && (
          <div className="flex items-center gap-2 rounded-xl border border-red-200 bg-red-50 p-3 text-xs text-red-700">
            <AlertCircle className="h-4 w-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Suggested Prompt Chips */}
      <div className="border-t border-slate-100 bg-slate-50/50 px-4 py-2.5">
        <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 mb-1.5">
          Suggested Questions:
        </p>
        <div className="flex flex-wrap gap-1.5 overflow-x-auto pb-1">
          {SUGGESTED_QUESTIONS.map((chip, idx) => (
            <button
              key={idx}
              disabled={loading}
              onClick={() => handleSend(chip)}
              className="inline-flex items-center gap-1 rounded-full border border-slate-200 bg-white px-2.5 py-1 text-xs text-slate-700 hover:border-emerald-300 hover:bg-emerald-50/60 hover:text-emerald-900 transition-colors disabled:opacity-50"
            >
              <Sparkles className="h-3 w-3 text-emerald-600" />
              <span>{chip}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Input Box */}
      <div className="border-t border-slate-200 p-3 bg-white">
        <div className="flex items-center gap-2">
          <input
            type="text"
            placeholder="Ask about district courses, demand, or skill expectations..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={loading}
            className="flex-1 rounded-xl border border-slate-300 px-4 py-2.5 text-sm focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500 disabled:opacity-50"
          />
          <button
            onClick={() => handleSend()}
            disabled={loading || !input.trim()}
            className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-emerald-600 text-white shadow-sm hover:bg-emerald-700 disabled:opacity-50 transition-colors"
          >
            <Send className="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>
  );
}

