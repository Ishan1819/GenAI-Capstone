import { useState } from "react";
import { Clock, MessageCircle } from "lucide-react";
import { api } from "../api.js";
import { DOMAINS } from "../data/isdic.js";
import { askUrl } from "../router.js";

export default function Projects({ initialDomain = "" }) {
  const [domainId, setDomainId] = useState(DOMAINS.some((d) => d.id === initialDomain) ? initialDomain : DOMAINS[0].id);
  const domain = DOMAINS.find((d) => d.id === domainId);
  const [level, setLevel] = useState(domain.levels[0].name);
  const [interests, setInterests] = useState("");
  const [skills, setSkills] = useState("");
  const [data, setData] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  function pickDomain(id) {
    setDomainId(id);
    setLevel(DOMAINS.find((d) => d.id === id).levels[0].name);
  }

  async function submit(e) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      setData(await api.projects({
        domain: domain.community, level, interests,
        skills: skills.split(",").map((s) => s.trim()).filter(Boolean),
      }));
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section>
      <form className="panel stack wide" onSubmit={submit}>
        <div className="filters">
          <label>Domain
            <select value={domainId} onChange={(e) => pickDomain(e.target.value)}>
              {DOMAINS.map((d) => <option key={d.id} value={d.id}>{d.community}</option>)}
            </select>
          </label>
          <label>Your level
            <select value={level} onChange={(e) => setLevel(e.target.value)}>
              {domain.levels.map((l) => <option key={l.name} value={l.name}>{l.name}</option>)}
            </select>
          </label>
        </div>
        <label>What are you interested in? (optional)
          <input value={interests} onChange={(e) => setInterests(e.target.value)} placeholder="e.g. healthcare, fintech, open source" />
        </label>
        <label>Skills you already have (optional, comma separated)
          <input value={skills} onChange={(e) => setSkills(e.target.value)} placeholder="e.g. Python, Linux" />
        </label>
        <div><button disabled={busy}>{busy ? "Thinking up projects…" : "Suggest projects"}</button></div>
      </form>
      {error && <p className="error">{error}</p>}

      {data && (
        <div className="project-grid">
          {data.projects.map((p, i) => (
            <article className="card project" key={i}>
              <div className="project-meta">
                {p.difficulty && <span className="tag">{p.difficulty}</span>}
                {p.duration && <span className="small muted"><Clock size={13} /> {p.duration}</span>}
              </div>
              <h3>{p.title}</h3>
              <p>{p.summary}</p>
              {p.steps?.length > 0 && (
                <ol className="project-steps">{p.steps.map((s, j) => <li key={j}>{s}</li>)}</ol>
              )}
              <div className="chips">
                {[...(p.tools || []), ...(p.skills || [])].slice(0, 8).map((t) => <span key={t} className="chip static">{t}</span>)}
              </div>
              {p.portfolio_value && <p className="small value"><b>Why it matters:</b> {p.portfolio_value}</p>}
              <a className="btn ghost small-btn" href={askUrl(`How do I start the project "${p.title}" in the ${domain.community}?`)}>
                <MessageCircle size={14} /> Ask how to start
              </a>
            </article>
          ))}
        </div>
      )}
      {data?.sources.length > 0 && (
        <p className="muted small">Grounded in: {data.sources.map((s) => <a key={s.url} href={s.url} target="_blank" rel="noreferrer">{s.title.replace(" | ISDIC", "")} · </a>)}</p>
      )}
    </section>
  );
}
