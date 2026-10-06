import React, { useEffect, useRef, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { addDays, format, startOfWeek, subWeeks, addWeeks } from "date-fns";
import { Brain, ChevronLeft, ChevronRight, Save, Send, Zap } from "lucide-react";
import { coachAPI, streamSSE } from "../api/client";
import Markdown from "../components/Markdown";
import "../styles/pages.css";
import "./WeeklyCoaching.css";

const MODELS = [
  { id: "CLAUDE_OPUS", label: "Claude Opus 5 (best)" },
  { id: "CLAUDE_SONNET", label: "Claude Sonnet 5" },
  { id: "CLAUDE_HAIKU", label: "Claude Haiku 4.5" },
  { id: "GEMINI_FREE", label: "Gemini Flash (free)" },
];

function lastCompletedWeek() {
  // On Sunday you recap the week ending today; otherwise last full week.
  const today = new Date();
  const monday = startOfWeek(today, { weekStartsOn: 1 });
  return today.getDay() === 0 ? monday : subWeeks(monday, 1);
}

function PlanPreview({ plan }) {
  if (!plan) return null;
  return (
    <div className="plan-preview card">
      <h3>
        Plan for week of {plan.startDate} · {plan.plannedTSS?.min}-{plan.plannedTSS?.max} TSS · FTP {plan.ftp}W
      </h3>
      <div className="plan-days">
        {(plan.days || []).map((day) => (
          <div key={day.dayNumber} className="plan-day">
            <div className="plan-day-date">{day.date}</div>
            {(day.workouts || []).map((w, i) => (
              <div key={i} className="plan-workout">
                <strong>{w.name}</strong>
                <span>
                  {w.type}
                  {w.plannedDuration ? ` · ${w.plannedDuration} min` : ""}
                  {w.plannedTSS?.max ? ` · ${w.plannedTSS.min}-${w.plannedTSS.max} TSS` : ""}
                </span>
              </div>
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}

function WeeklyCoaching() {
  const [weekStart, setWeekStart] = useState(lastCompletedWeek());
  const [model, setModel] = useState("CLAUDE_OPUS");
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState("");
  const [status, setStatus] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const bottomRef = useRef(null);
  const queryClient = useQueryClient();
  const weekStr = format(weekStart, "yyyy-MM-dd");
  const key = ["coachSession", weekStr, model];

  const { data: session, isLoading } = useQuery({
    queryKey: key,
    queryFn: async () => (await coachAPI.getSession(weekStr, model)).data,
  });

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [session?.messages?.length, streaming]);

  const run = async (path, extra = {}) => {
    setBusy(true);
    setError("");
    setNotice("");
    setStreaming("");
    let text = "";
    try {
      await streamSSE(path, { week_start: weekStr, model, ...extra }, (event) => {
        if (event.type === "text") {
          text += event.text;
          setStreaming(text);
          setStatus("");
        } else if (event.type === "status") {
          setStatus(event.text);
        } else if (event.type === "error") {
          setError(event.text);
        } else if (event.type === "done" && event.cost) {
          setNotice(`Session cost so far: $${event.cost.toFixed(2)}`);
        }
      });
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
      setStatus("");
      setStreaming("");
      await queryClient.invalidateQueries({ queryKey: key });
    }
  };

  const send = (e) => {
    e.preventDefault();
    const message = input.trim();
    if (!message) return;
    setInput("");
    if (session?.phase === "REVIEWING" && session?.current_plan) {
      run("/coach/session/edit", { feedback: message });
    } else {
      run("/coach/session/message", { message });
    }
  };

  const save = async () => {
    setBusy(true);
    setError("");
    try {
      const res = await coachAPI.savePlan(weekStr, model);
      setNotice(`${res.data.message} · ${res.data.zwift_files?.length || 0} Zwift files`);
      await queryClient.invalidateQueries();
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    } finally {
      setBusy(false);
    }
  };

  const messages = session?.messages || [];
  const phase = session?.phase || "ANALYSIS";
  const latestRecap = lastCompletedWeek();
  const weekFinished = weekStart <= latestRecap;

  return (
    <div className="page-container coaching-page">
      <div className="page-header coaching-header">
        <div>
          <h1 className="page-title">
            <Brain size={28} /> Weekly Coaching
          </h1>
          <p className="header-subtitle">
            Recap of {format(weekStart, "MMM d")}–{format(addDays(weekStart, 6), "MMM d")} · phase {phase}
          </p>
        </div>
        <div className="coaching-controls">
          <button className="btn btn-outline icon-btn" onClick={() => setWeekStart((w) => subWeeks(w, 1))}>
            <ChevronLeft size={18} />
          </button>
          <button className="btn btn-outline icon-btn" disabled={!weekFinished || weekStart >= latestRecap}
                  onClick={() => setWeekStart((w) => addWeeks(w, 1))}>
            <ChevronRight size={18} />
          </button>
          <select className="input" value={model} onChange={(e) => setModel(e.target.value)} disabled={busy}>
            {MODELS.map((m) => (
              <option key={m.id} value={m.id}>
                {m.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="chat card">
        {isLoading && <div className="spinner">Loading session…</div>}
        {!isLoading && messages.length === 0 && !busy && (
          <div className="chat-empty">
            {weekFinished ? (
              <>
                <p>Your coach will review the week, check your training load and history, and ask a couple of questions.</p>
                <button className="btn btn-primary" onClick={() => run("/coach/session/begin")}>
                  Begin coaching session
                </button>
              </>
            ) : (
              <p>This week isn't over yet — the recap opens on Sunday {format(addDays(weekStart, 6), "MMM d")}.</p>
            )}
          </div>
        )}
        {messages.map((m, i) => (
          <div key={i} className={`chat-msg ${m.role}`}>
            {m.role === "assistant" ? <Markdown>{m.content}</Markdown> : m.content}
          </div>
        ))}
        {busy && (
          <div className="chat-msg assistant">
            {status && <div className="chat-status">🔎 {status}…</div>}
            {streaming ? <Markdown>{streaming}</Markdown> : !status && <span className="chat-status">Thinking…</span>}
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {error && <div className="error-message">{error}</div>}
      {notice && <div className="notice">{notice}</div>}

      {messages.length > 0 && phase !== "SAVED" && (
        <form className="chat-input" onSubmit={send}>
          <textarea
            className="input"
            rows={2}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={phase === "REVIEWING" ? "Ask for changes to specific days…" : "Reply to your coach…"}
            disabled={busy}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) send(e);
            }}
          />
          <button className="btn btn-primary" type="submit" disabled={busy || !input.trim()}>
            <Send size={16} />
          </button>
        </form>
      )}

      <div className="coaching-actions">
        {messages.length > 0 && !session?.current_plan && (
          <button className="btn btn-secondary" disabled={busy} onClick={() => run("/coach/session/generate")}>
            <Zap size={16} /> Generate my plan now
          </button>
        )}
        {session?.current_plan && phase !== "SAVED" && (
          <button className="btn btn-primary" disabled={busy} onClick={save}>
            <Save size={16} /> Save plan &amp; generate Zwift files
          </button>
        )}
      </div>

      <PlanPreview plan={session?.current_plan} />
    </div>
  );
}

export default WeeklyCoaching;
