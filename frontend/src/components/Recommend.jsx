import { useEffect, useState } from "react";
import { api } from "../api.js";

function Item({ item }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="card">
      <strong>{item.name}</strong>
      <p className="muted small">{item.subtitle}</p>
      <p>{item.explanation}</p>
      <button className="link" onClick={() => setOpen(!open)}>{open ? "Hide graph evidence" : "Show graph evidence"}</button>
      {open && <ul className="small">{item.evidence.map((e, i) => <li key={i}>{e}</li>)}</ul>}
    </div>
  );
}

function Group({ title, items }) {
  return (
    <div>
      <h3>{title}</h3>
      {items.length ? items.map((it) => <Item key={it.id} item={it} />) : <p className="muted">Nothing to suggest.</p>}
    </div>
  );
}

export default function Recommend() {
  const [members, setMembers] = useState([]);
  const [selected, setSelected] = useState("");
  const [data, setData] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    api.members().then((m) => { setMembers(m); if (m.length) setSelected(m[0].id); }).catch((e) => setError(e.message));
  }, []);

  async function load() {
    setBusy(true);
    setError("");
    try {
      setData(await api.recommendations(selected));
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  const m = data?.member;
  return (
    <section>
      <div className="row panel">
        <select value={selected} onChange={(e) => setSelected(e.target.value)}>
          {members.map((x) => <option key={x.id} value={x.id}>{x.name} — {x.level} {x.domain}, {x.chapter}</option>)}
        </select>
        <button onClick={load} disabled={busy || !selected}>{busy ? "Thinking…" : "Recommend"}</button>
      </div>
      {members.length === 0 && !error && <p className="muted">No demo members yet. Run <code>python -m scripts.generate_demo_data</code>.</p>}
      {error && <p className="error">{error}</p>}
      {m && (
        <div className="card">
          <strong>{m.name}</strong> <span className="tag">{m.role}</span>
          <p className="muted small">{m.level} · {m.domain} · {m.chapter} · {m.college}</p>
          <p className="small">Skills: {m.skills.join(", ")} · Interests: {m.interests.join(", ")}</p>
        </div>
      )}
      {data && (
        <div className="grid3">
          <Group title="People to connect with" items={data.peers} />
          <Group title="Upcoming events" items={data.events} />
          <Group title="Curriculum modules" items={data.modules} />
        </div>
      )}
      {data?.notes.map((n, i) => <p className="muted small" key={i}>{n}</p>)}
    </section>
  );
}
