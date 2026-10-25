import React, { useEffect, useRef, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { addDays, format, startOfWeek, subWeeks, addWeeks } from "date-fns";
import { ChevronLeft, ChevronRight, Save, Send, Zap } from "lucide-react";
import { coachAPI, streamSSE } from "../api/client";
import Markdown from "../components/Markdown";
import WeekReview from "../components/WeekReview";
import CoachLogo from "../components/CoachLogo";
import apiClient from "../api/client";
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

function currentWeek() {
  return startOfWeek(new Date(), { weekStartsOn: 1 });
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
  const [step, setStep] = useState(null); // "review" | "coach"; null = pick automatically
  const bottomRef = useRef(null);
  // Once last week's plan is saved there's nothing left to do there: open the current
  // week so its workouts can be matched as they come in. Only on first load.
  const autoPicked = useRef(false);
  const queryClient = useQueryClient();
  const weekStr = format(weekStart, "yyyy-MM-dd");
  const key = ["coachSession", weekStr, model];

  const { data: session, isLoading } = useQuery({
    queryKey: key,
    queryFn: async () => (await coachAPI.getSession(weekStr, model)).data,
  });

  const { data: review } = useQuery({
    queryKey: ["review", weekStr],
    queryFn: async () => (await apiClient.get("/review/week", { params: { week_start: weekStr } })).data,
  });
  const toConfirm = review?.workouts?.filter((w) => w.status === "suggested").length ?? 0;

  // Scroll the chat box itself (not the page) to the newest message.
  useEffect(() => {
    const box = bottomRef.current?.parentElement;
    if (box) box.scrollTop = box.scrollHeight;
  }, [session?.messages?.length, streaming]);

  useEffect(() => setStep(null), [weekStr]);

  useEffect(() => {
    if (autoPicked.current || !session) return;
    autoPicked.current = true;
    if (session.phase === "SAVED" && weekStart < currentWeek()) setWeekStart(currentWeek());
  }, [session, weekStart]);

  const goToWeek = (w) => {
    autoPicked.current = true;
    setWeekStart(w);
  };

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
      // The save runs on the server (Zwift files take a few minutes); poll until it's done.
      let job = (await coachAPI.savePlan(weekStr, model)).data;
      const started = Date.now();
      while (job.state === "running") {
        const mins = Math.floor((Date.now() - started) / 60000);
        setStatus(`Saving the plan and building Zwift files${mins ? ` (${mins} min so far)` : ""}`);
        await new Promise((r) => setTimeout(r, 3000));
        job = (await coachAPI.saveStatus(weekStr)).data;
      }
      if (job.state === "error") throw new Error(job.message || "Saving failed");
      setNotice(`${job.message} · ${job.zwift_files?.length || 0} Zwift files`);
      await queryClient.invalidateQueries();
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    } finally {
      setStatus("");
      setBusy(false);
    }
  };

  const messages = session?.messages || [];
  const phase = session?.phase || "ANALYSIS";
  const latestRecap = lastCompletedWeek();
  const weekFinished = weekStart <= latestRecap;
  const thisWeek = currentWeek();
  const range = `${format(weekStart, "MMM d")}–${format(addDays(weekStart, 6), "MMM d")}`;
  // Start on the review step until the conversation has begun.
  const activeStep = step || (messages.length === 0 ? "review" : "coach");

  return (
    <div className="page-container coaching-page">
      <div className="page-header coaching-header">
        <div>
          <h1 className="page-title">
            <CoachLogo size={28} /> Weekly Coaching
          </h1>
          <p className="header-subtitle">
            {weekFinished
              ? <>Recap of {range}{phase === "SAVED" ? " · plan saved" : ""}</>
              : <>This week, {range} · match workouts as you go; the coach opens Sunday</>}
          </p>
        </div>
        <div className="coaching-controls">
          <button className="btn btn-outline icon-btn" title="Previous week" onClick={() => goToWeek(subWeeks(weekStart, 1))}>
            <ChevronLeft size={18} />
          </button>
          <button className="btn btn-outline icon-btn" title="Next week" disabled={weekStart >= thisWeek}
                  onClick={() => goToWeek(addWeeks(weekStart, 1))}>
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

      <div className="coaching-steps" role="tablist">
        <button role="tab" aria-selected={activeStep === "review"}
                className={`step-tab ${activeStep === "review" ? "active" : ""}`} onClick={() => setStep("review")}>
          ① Review week{toConfirm > 0 && <span className="step-badge">{toConfirm} to confirm</span>}
        </button>
        <button role="tab" aria-selected={activeStep === "coach"}
                className={`step-tab ${activeStep === "coach" ? "active" : ""}`} onClick={() => setStep("coach")}>
          ② Coach &amp; plan
        </button>
      </div>

      {activeStep === "review" && <WeekReview weekStart={weekStr} onDone={() => setStep("coach")} />}

      {activeStep === "coach" && (
      <>
      {toConfirm > 0 && messages.length === 0 && (
        <div className="notice">
          {toConfirm} workout(s) aren't confirmed yet — the coach works best when the week is reviewed first.
        </div>
      )}
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
              <p>
                This week isn't over yet. The coaching session opens on Sunday {format(addDays(weekStart, 6), "MMM d")};
                until then, match workouts in <button className="link-btn" onClick={() => setStep("review")}>① Review week</button>.
              </p>
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

      {phase === "SAVED" && !busy && (
        <div className="notice">
          This week's coaching is done: the plan for the week of {format(addWeeks(weekStart, 1), "MMM d")} was saved.
          {weekStart < thisWeek && (
            <> <button className="link-btn" onClick={() => goToWeek(addWeeks(weekStart, 1))}>
              Go to the week of {format(addWeeks(weekStart, 1), "MMM d")} →
            </button></>
          )}
        </div>
      )}
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
      </>
      )}
    </div>
  );
}

export default WeeklyCoaching;
