import { useEffect, useState } from "react";

export default function Queue({ api }) {
  const [items, setItems] = useState(null);
  const [drafts, setDrafts] = useState({});
  const [error, setError] = useState("");

  async function load() {
    setError("");
    try {
      setItems(await api.unanswered());
    } catch (e) {
      setError(e.message);
    }
  }
  useEffect(() => { load(); }, []);

  async function act(fn) {
    try {
      await fn();
      load();
    } catch (e) {
      setError(e.message);
    }
  }

  return (
    <div>
      <p className="muted">Questions the assistant refused to guess at. Your answer is added to the knowledge base, so the next member who asks gets it.</p>
      <button className="secondary" onClick={load}>Refresh</button>
      {error && <p className="error">{error}</p>}
      {items?.length === 0 && <div className="card"><p className="muted">Nothing waiting. 🎉</p></div>}
      {items?.map((it) => (
        <div className="card" key={it.id}>
          <p className="small muted">{new Date(it.ts * 1000).toLocaleString()}</p>
          <p><strong>{it.question}</strong></p>
          <textarea rows="3" placeholder="Write the answer…" value={drafts[it.id] || ""}
            onChange={(e) => setDrafts({ ...drafts, [it.id]: e.target.value })} />
          <div className="row" style={{ marginTop: 10 }}>
            <button disabled={(drafts[it.id] || "").trim().length < 3}
              onClick={() => act(() => api.answer(it.id, drafts[it.id]))}>Answer &amp; add to knowledge base</button>
            <button className="secondary" onClick={() => act(() => api.dismiss(it.id))}>Dismiss</button>
          </div>
        </div>
      ))}
    </div>
  );
}
