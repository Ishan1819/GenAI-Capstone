import { ArrowRight, Award, Bot, ExternalLink, Hammer, ListChecks, Route, Target, Wrench } from "lucide-react";
import { DOMAINS, SITE } from "../data/isdic.js";
import { askUrl } from "../router.js";
import { DOMAIN_ICONS } from "./Home.jsx";

const URL_SLUG = { cyber: "cyber", aiml: "aiml", cloud: "cloud", dev: "dev" };

export default function Domain({ id }) {
  const d = DOMAINS.find((x) => x.id === id);
  if (!d) return <div className="container section"><p>Domain not found. <a href="#/">Go home</a></p></div>;
  const Icon = DOMAIN_ICONS[d.id];

  return (
    <div style={{ "--c": d.color }}>
      <section className="domain-hero">
        <div className="container">
          <a href="#/" className="back small">← All domains</a>
          <div className="domain-title">
            <span className="domain-icon big"><Icon size={28} /></span>
            <div>
              <p className="eyebrow">Domain community</p>
              <h1>{d.community}</h1>
            </div>
          </div>
          <p className="lead">{d.tagline}</p>
          <div className="chips">{d.highlights.map((h) => <span key={h} className="chip static">{h}</span>)}</div>
          <div className="hero-actions">
            <a className="btn" href={askUrl(`Tell me about the ${d.community}`)}><Bot size={16} /> Ask about this track</a>
            <a className="btn ghost" href={`#/path?domain=${encodeURIComponent(d.name)}`}><Route size={16} /> Build my learning path</a>
            <a className="btn ghost" href={`#/quiz?domain=${d.id}`}><ListChecks size={16} /> Take the skill quiz</a>
            <a className="btn ghost" href={`#/projects?domain=${d.id}`}><Hammer size={16} /> Project ideas</a>
            <a className="btn ghost" href={`${SITE}/curriculum/${URL_SLUG[d.id]}`} target="_blank" rel="noreferrer">
              Official plan <ExternalLink size={14} />
            </a>
          </div>
        </div>
      </section>

      <section className="section">
        <div className="container">
          <h2>Skill progression</h2>
          <div className="level-grid">
            {d.levels.map((l, i) => (
              <div key={l.name} className="level-card">
                <span className="level-num">Level 0{i + 1}</span>
                <h3>{l.name}</h3>
                <p className="muted small">{l.months}</p>
                <ul>{l.items.map((it) => <li key={it}>{it}</li>)}</ul>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="section alt">
        <div className="container two-col">
          <div className="flagship">
            <p className="eyebrow"><Award size={14} /> Flagship event</p>
            <h2>{d.flagship.name}</h2>
            <p>{d.flagship.text}</p>
            <div className="chips">{d.flagship.tags.map((t) => <span key={t} className="chip static">{t}</span>)}</div>
          </div>
          <div>
            <p className="eyebrow"><Wrench size={14} /> Tools used</p>
            <div className="tool-chips">{d.tools.map((t) => <span key={t}>{t}</span>)}</div>
          </div>
        </div>
      </section>

      <section className="section">
        <div className="container">
          <p className="eyebrow"><Target size={14} /> Target outcomes</p>
          <h2>What members leave with</h2>
          <div className="outcome-grid">
            {d.outcomes.map((o) => (
              <div key={o.title} className="outcome"><h3>{o.title}</h3><p className="muted">{o.text}</p></div>
            ))}
          </div>

          <div className="ask-panel">
            <h3><Bot size={18} /> Questions people ask about this track</h3>
            <div className="chips">
              {d.questions.map((q) => <a key={q} className="chip" href={askUrl(q)}>{q}</a>)}
            </div>
          </div>

          <h3 className="other-title">Other communities</h3>
          <div className="other-grid">
            {DOMAINS.filter((x) => x.id !== d.id).map((x) => {
              const I = DOMAIN_ICONS[x.id];
              return (
                <a key={x.id} href={`#/domains/${x.id}`} className="other" style={{ "--c": x.color }}>
                  <I size={18} /> {x.community} <ArrowRight size={14} />
                </a>
              );
            })}
          </div>
        </div>
      </section>
    </div>
  );
}
