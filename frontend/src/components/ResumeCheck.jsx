import { useState } from "react";
import { api } from "../api.js";

const List = ({ items }) => (
  <div>{(items || []).map((s, i) => <span className="tag" key={i}>{s}</span>)}</div>
);

export default function ResumeCheck() {
  const [file, setFile] = useState(null);
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function submit(e) {
    e.preventDefault();
    if (!file) return;
    setBusy(true);
    setError("");
    try {
      setResult(await api.resume(file));
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section>
      <form className="stack panel" onSubmit={submit}>
        <input type="file" accept=".pdf,.txt" onChange={(e) => setFile(e.target.files[0])} />
        <button disabled={busy || !file}>{busy ? "Analysing…" : "Analyse"}</button>
      </form>
      {error && <p className="error">{error}</p>}
      {result && (
        <div className="card">
          <p><strong>Recommended:</strong> {result.recommended_domain} · <span className="tag">{result.recommended_level}</span></p>
          <p>{result.level_reason}</p>
          <h4>Skills we found</h4><List items={result.matched_skills?.length ? result.matched_skills : result.detected_skills} />
          <h4>Skills to build</h4><List items={result.missing_skills} />
          <h4>Recommended modules</h4>
          <ul>{(result.recommended_modules || []).map((m, i) => <li key={i}><strong>{m.name}</strong> – {m.reason}</li>)}</ul>
          <p>{result.summary}</p>
        </div>
      )}
    </section>
  );
}
