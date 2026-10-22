import { useEffect, useRef, useState } from "react";
import { Bot, ChevronDown, ChevronUp, Send } from "lucide-react";
import { api } from "../api.js";
import GraphView from "./GraphView.jsx";

const STARTERS = [
  "What is ISDIC and who is it for?",
  "What are the three skill levels in the AI & ML track?",
  "Which members in AI and ML are interested in healthcare?",
  "What is the flagship event of the cloud community?",
];

function Message({ m, onFollowup, compact }) {
  const [showWhy, setShowWhy] = useState(false);
  if (m.role === "user") return <div className="msg user">{m.text}</div>;
  const hasReasoning = m.reasoning && (m.reasoning.facts.length || m.reasoning.graph.nodes.length);
  return (
    <div className="msg-row">
      <span className="msg-avatar"><Bot size={16} /></span>
      <div className={`msg bot ${m.answered === false ? "unanswered" : ""}`}>
        <p className="answer">{m.text}</p>
        {m.sources?.length > 0 && (
          <div className="sources">
            {m.sources.map((s) => (
              <a key={s.n} href={s.url || undefined} target="_blank" rel="noreferrer" title={s.snippet}>
                <b>[{s.n}]</b> {s.title.replace(" | ISDIC", "")}
              </a>
            ))}
          </div>
        )}
        {hasReasoning && !compact && (
          <>
            <button className="link" onClick={() => setShowWhy(!showWhy)}>
              {showWhy ? <ChevronUp size={14} /> : <ChevronDown size={14} />} {showWhy ? "Hide reasoning" : "Show reasoning (knowledge graph)"}
            </button>
            {showWhy && (
              <div className="why">
                <GraphView graph={m.reasoning.graph} />
                <ul>{m.reasoning.facts.slice(0, 10).map((f, i) => <li key={i}>{f}</li>)}</ul>
              </div>
            )}
          </>
        )}
        {m.followups?.length > 0 && (
          <div className="followups">
            {m.followups.map((f, i) => <button key={i} onClick={() => onFollowup(f)}>{f}</button>)}
          </div>
        )}
      </div>
    </div>
  );
}

export default function Chat({ initialQuestion = "", compact = false }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const session = useRef(null);
  const asked = useRef(false);
  const end = useRef(null);

  useEffect(() => {
    if (initialQuestion && !asked.current) {
      asked.current = true;
      send(initialQuestion);
    }
  }, [initialQuestion]);

  useEffect(() => {
    end.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [messages, busy]);

  async function send(text) {
    text = text.trim();
    if (!text || busy) return;
    setInput("");
    setBusy(true);
    setMessages((m) => [...m, { role: "user", text }]);
    try {
      const res = await api.chat(text, session.current);
      session.current = res.session_id;
      setMessages((m) => [...m, { role: "bot", text: res.answer, answered: res.answered, sources: res.sources,
        followups: res.followups, reasoning: res.reasoning }]);
    } catch (e) {
      setMessages((m) => [...m, { role: "bot", text: `Something went wrong: ${e.message}`, answered: false }]);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className={`chat ${compact ? "compact" : ""}`}>
      <div className="messages">
        {messages.length === 0 && (
          <div className="chat-empty">
            <span className="tool-icon"><Bot size={22} /></span>
            <p><b>Hi! I'm the ISDIC assistant.</b><br />Ask about domains, curriculum levels, events, chapters or members.</p>
            <div className="chips">
              {STARTERS.slice(0, compact ? 3 : 4).map((s) => <button key={s} className="chip" onClick={() => send(s)}>{s}</button>)}
            </div>
          </div>
        )}
        {messages.map((m, i) => <Message key={i} m={m} onFollowup={send} compact={compact} />)}
        {busy && (
          <div className="msg-row">
            <span className="msg-avatar"><Bot size={16} /></span>
            <div className="msg bot typing"><span /><span /><span /></div>
          </div>
        )}
        <div ref={end} />
      </div>
      <form className="chat-input" onSubmit={(e) => { e.preventDefault(); send(input); }}>
        <input value={input} onChange={(e) => setInput(e.target.value)} placeholder="Ask a question…" />
        <button type="submit" disabled={busy || !input.trim()} aria-label="Send"><Send size={18} /></button>
      </form>
    </section>
  );
}
