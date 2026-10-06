import React, { useRef, useState } from "react";
import { MessageCircle, Send } from "lucide-react";
import { streamSSE } from "../api/client";
import Markdown from "./Markdown";
import "./AskCoach.css";

const SUGGESTIONS = [
  "Fueling plan for this session?",
  "Only have 45 minutes — what should I do instead?",
  "How hard should the main set feel?",
];

// Quick questions to the same coach about one day's workout.
function AskCoach({ date }) {
  const [history, setHistory] = useState([]);
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [status, setStatus] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const abortRef = useRef(null);

  const ask = async (text) => {
    const q = (text ?? question).trim();
    if (!q || busy) return;
    setBusy(true);
    setError("");
    setAnswer("");
    setQuestion("");
    abortRef.current = new AbortController();
    let full = "";
    try {
      await streamSSE(
        "/coach/ask",
        { date, question: q, history },
        (event) => {
          if (event.type === "text") {
            full += event.text;
            setAnswer(full);
            setStatus("");
          } else if (event.type === "status") {
            setStatus(event.text);
          } else if (event.type === "error") {
            setError(event.text);
          } else if (event.type === "done") {
            full = event.answer || full;
          }
        },
        { signal: abortRef.current.signal },
      );
      setHistory((h) => [...h, { role: "user", content: q }, { role: "assistant", content: full }]);
      setAnswer("");
    } catch (err) {
      if (err.name !== "AbortError") setError(err.message);
    } finally {
      setBusy(false);
      setStatus("");
    }
  };

  return (
    <div className="ask-coach">
      <h4>
        <MessageCircle size={18} /> Ask the coach
      </h4>
      <div className="ask-thread">
        {history.map((turn, i) => (
          <div key={i} className={`ask-turn ${turn.role}`}>
            {turn.role === "assistant" ? <Markdown>{turn.content}</Markdown> : turn.content}
          </div>
        ))}
        {busy && (
          <div className="ask-turn assistant">
            {answer ? <Markdown>{answer}</Markdown> : <span className="ask-status">{status ? `🔎 ${status}…` : "Thinking…"}</span>}
          </div>
        )}
        {error && <div className="ask-error">{error}</div>}
      </div>
      {history.length === 0 && !busy && (
        <div className="ask-suggestions">
          {SUGGESTIONS.map((s) => (
            <button key={s} className="btn btn-outline btn-sm" onClick={() => ask(s)}>
              {s}
            </button>
          ))}
        </div>
      )}
      <form
        className="ask-input"
        onSubmit={(e) => {
          e.preventDefault();
          ask();
        }}
      >
        <input
          className="input"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Fueling, substitutions, what a movement is…"
          disabled={busy}
        />
        <button className="btn btn-primary" type="submit" disabled={busy || !question.trim()}>
          <Send size={16} />
        </button>
      </form>
    </div>
  );
}

export default AskCoach;
