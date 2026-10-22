import { useState } from "react";
import { Copy, Download, Wand2 } from "lucide-react";
import { DOMAINS, QUARTERS } from "../data/isdic.js";

const FORMATS = ["Workshop", "Hands-on lab", "Bootcamp", "Talk + Q&A", "Competition", "Study group"];
const LEVELS = ["Beginner", "Intermediate", "Advanced"];
const SHORT = { cyber: "Cyber", aiml: "AI & ML", cloud: "Cloud", dev: "Dev" };

function toMarkdown(p) {
  const lines = [`# ${p.title}`, "", p.summary, "", `**Audience:** ${p.audience}`, "", "## Objectives", ...p.objectives.map((o) => `- ${o}`)];
  if (p.prerequisites?.length) lines.push("", "## Prerequisites", ...p.prerequisites.map((o) => `- ${o}`));
  lines.push("", "## Agenda", "| Time | Segment | Activity |", "|---|---|---|", ...p.agenda.map((a) => `| ${a.time} | ${a.segment} | ${a.activity} |`));
  if (p.lab) lines.push("", `## Lab: ${p.lab.title}`, ...(p.lab.steps || []).map((s, i) => `${i + 1}. ${s}`), "", `Tools: ${(p.lab.tools || []).join(", ")}`);
  if (p.quiz?.length) lines.push("", "## Quick quiz", ...p.quiz.map((q, i) => `${i + 1}. ${q.question}\n   - Answer: ${q.answer}`));
  if (p.materials?.length) lines.push("", "## Prepare beforehand", ...p.materials.map((m) => `- ${m}`));
  if (p.follow_up) lines.push("", "## Follow-up", p.follow_up);
  return lines.join("\n");
}

export default function SessionPlanner({ api }) {
  const [domainId, setDomainId] = useState(DOMAINS[0].id);
  const domain = DOMAINS.find((d) => d.id === domainId);
  const [form, setForm] = useState({ topic: "", level: "Beginner", duration_hours: 3, format: "Workshop", notes: "" });
  const [plan, setPlan] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [copied, setCopied] = useState(false);
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  const suggestions = [
    ...domain.levels.flatMap((l) => l.items.slice(0, 2)),
    ...QUARTERS.flatMap((q) => q.items.filter(([d]) => d === SHORT[domainId]).map(([, item]) => item)),
  ].slice(0, 10);

  async function submit(e) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      setPlan(await api.sessionPlan({ ...form, duration_hours: Number(form.duration_hours), domain: domain.community }));
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  function download() {
    const blob = new Blob([toMarkdown(plan)], { type: "text/markdown" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `${plan.title.replace(/[^\w]+/g, "-").toLowerCase()}.md`;
    a.click();
    URL.revokeObjectURL(a.href);
  }

  async function copy() {
    try {
      await navigator.clipboard.writeText(toMarkdown(plan));
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {}
  }

  return (
    <div>
      <p className="muted">Turn any curriculum activity into a ready-to-run session: agenda, hands-on lab, quiz and prep list, using the track's own tools.</p>
      <form className="panel stack wide" onSubmit={submit}>
        <div className="filters">
          <label>Domain
            <select value={domainId} onChange={(e) => setDomainId(e.target.value)}>
              {DOMAINS.map((d) => <option key={d.id} value={d.id}>{d.community}</option>)}
            </select>
          </label>
          <label>Format
            <select value={form.format} onChange={set("format")}>{FORMATS.map((f) => <option key={f}>{f}</option>)}</select>
          </label>
          <label>Audience level
            <select value={form.level} onChange={set("level")}>{LEVELS.map((l) => <option key={l}>{l}</option>)}</select>
          </label>
          <label>Duration (hours)
            <input type="number" min="0.5" max="16" step="0.5" value={form.duration_hours} onChange={set("duration_hours")} />
          </label>
        </div>
        <label>Topic<input value={form.topic} onChange={set("topic")} placeholder="e.g. OWASP Top 10 in practice" required /></label>
        <div className="chips">{suggestions.map((s) => <button type="button" key={s} className="chip" onClick={() => setForm({ ...form, topic: s })}>{s}</button>)}</div>
        <label>Notes for the planner (optional)
          <input value={form.notes} onChange={set("notes")} placeholder="e.g. 40 students, college lab with no admin rights" />
        </label>
        <div><button disabled={busy || form.topic.trim().length < 3}><Wand2 size={16} /> {busy ? "Planning…" : "Generate session plan"}</button></div>
      </form>
      {error && <p className="error">{error}</p>}

      {plan && (
        <article className="card plan">
          <div className="plan-head">
            <div>
              <p className="eyebrow">{form.format} · {form.duration_hours} h · {form.level}</p>
              <h2>{plan.title}</h2>
              <p>{plan.summary}</p>
              {plan.audience && <p className="small muted">Audience: {plan.audience}</p>}
            </div>
            <div className="row">
              <button className="secondary" onClick={copy}><Copy size={15} /> {copied ? "Copied" : "Copy"}</button>
              <button className="secondary" onClick={download}><Download size={15} /> Markdown</button>
            </div>
          </div>
          <div className="admin-two">
            <div><h3>Objectives</h3><ul>{plan.objectives?.map((o, i) => <li key={i}>{o}</li>)}</ul></div>
            <div><h3>Prerequisites</h3><ul>{plan.prerequisites?.map((o, i) => <li key={i}>{o}</li>)}</ul></div>
          </div>
          <h3>Agenda</h3>
          <table>
            <thead><tr><th>Time</th><th>Segment</th><th>Activity</th></tr></thead>
            <tbody>{plan.agenda.map((a, i) => <tr key={i}><td className="nowrap">{a.time}</td><td>{a.segment}</td><td>{a.activity}</td></tr>)}</tbody>
          </table>
          {plan.lab && (
            <>
              <h3>Lab: {plan.lab.title}</h3>
              <ol>{plan.lab.steps?.map((s, i) => <li key={i}>{s}</li>)}</ol>
              <div className="chips">{plan.lab.tools?.map((t) => <span key={t} className="chip static">{t}</span>)}</div>
            </>
          )}
          <div className="admin-two">
            <div>
              <h3>Quick quiz</h3>
              <ol>{plan.quiz?.map((q, i) => <li key={i}>{q.question}<br /><span className="small muted">Answer: {q.answer}</span></li>)}</ol>
            </div>
            <div>
              <h3>Prepare beforehand</h3>
              <ul>{plan.materials?.map((m, i) => <li key={i}>{m}</li>)}</ul>
              {plan.follow_up && <><h3>Follow-up</h3><p>{plan.follow_up}</p></>}
            </div>
          </div>
        </article>
      )}
    </div>
  );
}
