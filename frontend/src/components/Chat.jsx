import { useEffect, useRef, useState } from "react";
import { Bot, Send } from "lucide-react";
import { api } from "../api.js";

const STARTERS = [
  "What is ISDIC and who is it for?",
  "What are the three skill levels in the AI & ML track?",
  "Is ISDIC free for students and colleges?",
  "What is the flagship event of the cloud community?",
];

function Message({ m, onFollowup }) {
  if (m.role === "user") return <div className="msg user">{m.text}</div>;
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
        followups: res.followups }]);
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
            <p><b>Hi! I'm the ISDIC assistant.</b><br />Ask about domains, curriculum levels, events, chapters or how to join.</p>
            <div className="chips">
              {STARTERS.slice(0, compact ? 3 : 4).map((s) => <button key={s} className="chip" onClick={() => send(s)}>{s}</button>)}
            </div>
          </div>
        )}
        {messages.map((m, i) => <Message key={i} m={m} onFollowup={send} />)}
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
