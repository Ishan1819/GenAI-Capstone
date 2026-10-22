import { useState } from "react";
import { Sparkles } from "lucide-react";

export default function Overview({ api }) {
  const [data, setData] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function load() {
    setBusy(true);
    setError("");
    try {
      setData(await api.insights());
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <p className="muted">What members are asking the assistant, what it couldn't answer, and where demand outruns the curriculum.</p>
      <button onClick={load} disabled={busy}><Sparkles size={16} /> {busy ? "Analysing activity…" : data ? "Refresh insights" : "Generate insights"}</button>
      {error && <p className="error">{error}</p>}
      {data && (
        <>
          <div className="stats">
            <div><b>{data.total_questions}</b><span>questions asked</span></div>
            <div><b>{data.answered_rate == null ? "–" : `${Math.round(data.answered_rate * 100)}%`}</b><span>answered from sources</span></div>
            <div><b>{data.knowledge_gaps.length}</b><span>gap topics</span></div>
            <div><b>{data.graph.nodes}</b><span>graph entities</span></div>
            <div><b>{data.graph.edges}</b><span>relationships</span></div>
          </div>
          {data.narrative && <div className="card narrative"><h3>AI summary</h3>{data.narrative}</div>}
          <div className="admin-two">
            <div className="card">
              <h3>Trending questions</h3>
              {data.top_topics.length === 0 && <p className="muted">No questions yet.</p>}
              <ul className="rank-list">{data.top_topics.map((t, i) => <li key={i}><span>{t.label}</span><span className="tag">{t.count}</span></li>)}</ul>
            </div>
            <div className="card">
              <h3>Knowledge gaps</h3>
              <p className="small muted">Topics the assistant couldn't answer from ISDIC's content.</p>
              {data.knowledge_gaps.length === 0 && <p className="muted">None so far.</p>}
              <ul className="rank-list">{data.knowledge_gaps.map((t, i) => <li key={i}><span>{t.label}</span><span className="tag">{t.count}</span></li>)}</ul>
            </div>
          </div>
          <div className="card">
            <h3>Demand vs. curriculum coverage</h3>
            <table>
              <thead><tr><th>Domain</th><th>Questions asked</th><th>Modules in curriculum</th></tr></thead>
              <tbody>{data.domain_demand.map((d) => <tr key={d.domain}><td>{d.domain}</td><td>{d.questions}</td><td>{d.modules}</td></tr>)}</tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
