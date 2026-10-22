import { useEffect, useState } from "react";
import { api } from "../api.js";

const EMPTY = { entity_type: "", domain: "", chapter: "", level: "", upcoming: false };

function Select({ label, value, options, onChange }) {
  return (
    <label>{label}
      <select value={value} onChange={(e) => onChange(e.target.value)}>
        <option value="">Any</option>
        {options.map((o) => <option key={o} value={o}>{o}</option>)}
      </select>
    </label>
  );
}

export default function Search() {
  const [query, setQuery] = useState("");
  const [filters, setFilters] = useState(EMPTY);
  const [vocab, setVocab] = useState({ entity_types: [], domains: [], chapters: [], levels: [] });
  const [data, setData] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => { api.searchFilters().then(setVocab).catch(() => {}); }, []);
  const set = (key) => (val) => setFilters({ ...filters, [key]: val });

  async function submit(e) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      setData(await api.search({ query, ...filters }));
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  const u = data?.understood;
  return (
    <section>
      <form className="stack wide panel" onSubmit={submit}>
        <input value={query} onChange={(e) => setQuery(e.target.value)}
          placeholder='e.g. "beginner cybersecurity events in Pune" or "mentors who know Kubernetes"' />
        <div className="filters">
          <Select label="Type" value={filters.entity_type} options={vocab.entity_types} onChange={set("entity_type")} />
          <Select label="Domain" value={filters.domain} options={vocab.domains} onChange={set("domain")} />
          <Select label="Chapter" value={filters.chapter} options={vocab.chapters} onChange={set("chapter")} />
          <Select label="Level" value={filters.level} options={vocab.levels} onChange={set("level")} />
          <label className="check">
            <input type="checkbox" checked={filters.upcoming} onChange={(e) => set("upcoming")(e.target.checked)} /> Upcoming only
          </label>
        </div>
        <button disabled={busy}>{busy ? "Searching…" : "Search"}</button>
      </form>
      {error && <p className="error">{error}</p>}
      {u && (
        <p className="muted">
          Understood as:{" "}
          {["entity_type", "domain", "chapter", "level"].filter((f) => u[f]).map((f) => <span className="tag" key={f}>{u[f]}</span>)}
          {u.upcoming && <span className="tag">upcoming</span>}
          {u.semantic_query && <span className="tag">“{u.semantic_query}”</span>}
          <span className="small"> (parsed by {u.parser})</span>
        </p>
      )}
      {data && data.results.length === 0 && <p className="muted">No results match these filters.</p>}
      {data?.results.map((r) => (
        <div className="card" key={`${r.type}-${r.id}`}>
          <span className={`badge ${r.type}`}>{r.type}</span>{" "}
          {r.url ? <a href={r.url} target="_blank" rel="noreferrer"><strong>{r.title}</strong></a> : <strong>{r.title}</strong>}
          <span className="muted small"> · relevance {r.relevance}</span>
          <p className="muted">{r.subtitle}</p>
          <p className="small">{r.snippet}</p>
          {r.why.length > 0 && <p className="small">Why: {r.why.join(" · ")}</p>}
        </div>
      ))}
    </section>
  );
}
