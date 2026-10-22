import { useState } from "react";
import { Check, RotateCcw, X } from "lucide-react";
import { api } from "../api.js";
import { DOMAINS } from "../data/isdic.js";
import { askUrl } from "../router.js";

export default function Quiz({ initialDomain = "" }) {
  const [domainId, setDomainId] = useState(DOMAINS.some((d) => d.id === initialDomain) ? initialDomain : DOMAINS[0].id);
  const domain = DOMAINS.find((d) => d.id === domainId);
  const [level, setLevel] = useState(domain.levels[0].name);
  const [quiz, setQuiz] = useState(null);
  const [answers, setAnswers] = useState({});
  const [submitted, setSubmitted] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  function pickDomain(id) {
    setDomainId(id);
    setLevel(DOMAINS.find((d) => d.id === id).levels[0].name);
  }

  async function start(e) {
    e?.preventDefault();
    setBusy(true);
    setError("");
    setSubmitted(false);
    setAnswers({});
    try {
      setQuiz(await api.quiz({ domain: domain.community, level, count: 5 }));
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  const qs = quiz?.questions || [];
  const score = qs.filter((q, i) => answers[i] === q.answer_index).length;
  const pct = qs.length ? Math.round((score / qs.length) * 100) : 0;
  const missed = [...new Set(qs.filter((q, i) => answers[i] !== q.answer_index).map((q) => q.topic).filter(Boolean))];
  const levelIdx = domain.levels.findIndex((l) => l.name === level);
  const next = domain.levels[levelIdx + 1];

  return (
    <section>
      <form className="panel filters" onSubmit={start}>
        <label>Domain
          <select value={domainId} onChange={(e) => pickDomain(e.target.value)}>
            {DOMAINS.map((d) => <option key={d.id} value={d.id}>{d.community}</option>)}
          </select>
        </label>
        <label>Level
          <select value={level} onChange={(e) => setLevel(e.target.value)}>
            {domain.levels.map((l) => <option key={l.name} value={l.name}>{l.name} ({l.months})</option>)}
          </select>
        </label>
        <button disabled={busy}>{busy ? "Writing your quiz…" : quiz ? "New quiz" : "Start quiz"}</button>
      </form>
      {error && <p className="error">{error}</p>}

      {submitted && (
        <div className={`card result ${pct >= 80 ? "good" : ""}`}>
          <div className="score"><b>{score}/{qs.length}</b><span>{pct}%</span></div>
          <div>
            {pct >= 80 ? (
              <p><b>Strong result.</b> {next ? <>You look ready for <b>{next.name}</b> in {domain.community}.</> : "You're at the top level of this track."}</p>
            ) : (
              <p><b>Good start.</b> Review the topics below, then try another quiz at this level.</p>
            )}
            {missed.length > 0 && (
              <div className="chips">
                {missed.map((t) => <a key={t} className="chip" href={askUrl(`Explain ${t} for the ${domain.community}`)}>Learn: {t}</a>)}
              </div>
            )}
          </div>
        </div>
      )}

      {qs.map((q, i) => (
        <div className="card question" key={i}>
          <p className="q-title"><span className="q-num">{i + 1}</span> {q.question}</p>
          <div className="options">
            {q.options.map((opt, j) => {
              const chosen = answers[i] === j;
              const state = submitted ? (j === q.answer_index ? "correct" : chosen ? "wrong" : "") : chosen ? "chosen" : "";
              return (
                <button type="button" key={j} className={`option ${state}`} disabled={submitted}
                  onClick={() => setAnswers({ ...answers, [i]: j })}>
                  <span className="opt-letter">{"ABCD"[j]}</span> {opt}
                  {submitted && j === q.answer_index && <Check size={16} />}
                  {submitted && chosen && j !== q.answer_index && <X size={16} />}
                </button>
              );
            })}
          </div>
          {submitted && <p className="small muted explain">{q.explanation}</p>}
        </div>
      ))}

      {qs.length > 0 && (
        <div className="row">
          {!submitted ? (
            <button onClick={() => setSubmitted(true)} disabled={Object.keys(answers).length < qs.length}>
              Check answers ({Object.keys(answers).length}/{qs.length})
            </button>
          ) : (
            <button className="secondary" onClick={start}><RotateCcw size={16} /> Try another quiz</button>
          )}
        </div>
      )}
    </section>
  );
}
