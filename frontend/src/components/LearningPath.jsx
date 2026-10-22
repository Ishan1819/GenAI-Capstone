import { useState } from "react";
import { api } from "../api.js";

export default function LearningPath({ initialDomain = "" }) {
  const [goal, setGoal] = useState("");
  const [domain, setDomain] = useState(initialDomain);
  const [skills, setSkills] = useState("");
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function submit(e) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      setResult(await api.learningPath({
        goal, domain,
        current_skills: skills.split(",").map((s) => s.trim()).filter(Boolean),
      }));
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section>
      <form className="stack panel" onSubmit={submit}>
        <label>Your goal<input value={goal} onChange={(e) => setGoal(e.target.value)} placeholder="e.g. become a cloud engineer" required /></label>
        <label>Domain of interest (optional)<input value={domain} onChange={(e) => setDomain(e.target.value)} placeholder="e.g. Cloud and DevOps" /></label>
        <label>Skills you already have (comma separated)<input value={skills} onChange={(e) => setSkills(e.target.value)} placeholder="python, linux basics" /></label>
        <button disabled={busy}>{busy ? "Building…" : "Generate roadmap"}</button>
      </form>
      {error && <p className="error">{error}</p>}
      {result && (
        <div className="card">
          <p>{result.summary}</p>
          <ol className="steps">
            {result.steps.map((s, i) => (
              <li key={i}>
                <strong>{s.title}</strong> {s.level && <span className="tag">{s.level}</span>}
                <p>{s.why}</p>
                {s.skills_gained?.length > 0 && <p className="muted">Skills: {s.skills_gained.join(", ")}</p>}
              </li>
            ))}
          </ol>
          {result.sources.length > 0 && (
            <p className="muted">Based on: {result.sources.map((s) => <a key={s.url} href={s.url} target="_blank" rel="noreferrer">{s.title} </a>)}</p>
          )}
        </div>
      )}
    </section>
  );
}
