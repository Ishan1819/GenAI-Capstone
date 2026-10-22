import { useState } from "react";
import {
  ArrowRight, Bot, Brain, Building2, CalendarDays, Cloud, Code, ExternalLink, FileText, Hammer, ListChecks, MapPin,
  Route, Search, Send, Shield, Users,
} from "lucide-react";
import { CHAPTERS, DOMAINS, LEADERS, MODEL_STEPS, QUARTERS, SITE, STATS, WHY } from "../data/isdic.js";
import { askUrl, go } from "../router.js";

export const DOMAIN_ICONS = { cyber: Shield, aiml: Brain, cloud: Cloud, dev: Code };

const TOOLS = [
  { to: "/assistant", icon: Bot, title: "Ask the assistant", text: "Grounded answers from ISDIC's own content, with sources and the knowledge-graph path behind each answer." },
  { to: "/search", icon: Search, title: "Community search", text: "“Beginner cyber events in Pune” becomes filters plus a semantic search over members and events." },
  { to: "/path", icon: Route, title: "Learning path", text: "Tell us your goal and what you know; get a roadmap through the curriculum in prerequisite order." },
  { to: "/quiz", icon: ListChecks, title: "Skill quiz", text: "Five questions from your track's curriculum to check if you're ready for the next level." },
  { to: "/projects", icon: Hammer, title: "Project ideas", text: "Portfolio projects that use your track's tools, sized to your level and interests." },
  { to: "/resume", icon: FileText, title: "Resume check", text: "Upload your resume to find your best-fit domain and level, and the skills you still need." },
  { to: "/for-you", icon: Users, title: "For you", text: "Peers, events and modules recommended from the knowledge graph, each with a reason." },
];

const SUGGESTIONS = ["What is ISDIC?", "Is ISDIC free for students?", "How do I join the Pune chapter?", "What does the cloud track cover?"];

function Hero() {
  const [q, setQ] = useState("");
  const ask = (text) => text.trim() && go(askUrl(text.trim()).slice(1));
  return (
    <section className="hero">
      <div className="container hero-grid">
        <div>
          <p className="eyebrow">Industry Skill Development &amp; Innovation Cell</p>
          <h1>Industry-ready skills, <em>built inside the campus.</em></h1>
          <p className="lead">
            ISDIC embeds skill development centres inside colleges and runs community chapters across
            cybersecurity, AI &amp; ML, cloud &amp; DevOps and software development. Ask anything about it.
          </p>
          <form className="ask-box" onSubmit={(e) => { e.preventDefault(); ask(q); }}>
            <Bot size={20} className="ask-icon" />
            <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Ask about domains, levels, events, chapters…" />
            <button aria-label="Ask"><Send size={18} /></button>
          </form>
          <div className="chips">
            {SUGGESTIONS.map((s) => <button key={s} className="chip" onClick={() => ask(s)}>{s}</button>)}
          </div>
        </div>
        <aside className="hero-card">
          <p className="eyebrow">Flagship events</p>
          <h3>One headline event per domain, every year</h3>
          <ul className="flagship-list">
            {DOMAINS.map((d) => {
              const Icon = DOMAIN_ICONS[d.id];
              return (
                <li key={d.id} style={{ "--c": d.color }}>
                  <span className="domain-icon sm"><Icon size={16} /></span>
                  <a href={`#/domains/${d.id}`}><b>{d.flagship.name}</b><small>{d.community}</small></a>
                </li>
              );
            })}
          </ul>
          <a href="#/search" className="more">Find events near you <ArrowRight size={14} /></a>
        </aside>
      </div>
      <div className="container stats-strip">
        {STATS.map((s) => (
          <div key={s.label}><b>{s.value}</b><span>{s.label}</span></div>
        ))}
      </div>
    </section>
  );
}

export default function Home() {
  return (
    <>
      <Hero />

      <section className="section">
        <div className="container">
          <div className="section-head">
            <p className="eyebrow">AI tools</p>
            <h2>One platform for every member</h2>
            <p className="lead">Built on a hybrid knowledge graph + vector retrieval backbone over ISDIC's community knowledge.</p>
          </div>
          <div className="tool-grid">
            {TOOLS.map(({ to, icon: Icon, title, text }) => (
              <a key={to} href={`#${to}`} className="tool-card">
                <span className="tool-icon"><Icon size={20} /></span>
                <h3>{title}</h3>
                <p>{text}</p>
                <span className="more">Open <ArrowRight size={14} /></span>
              </a>
            ))}
          </div>
        </div>
      </section>

      <section className="section alt">
        <div className="container">
          <div className="section-head">
            <p className="eyebrow">Core domains</p>
            <h2>Pick your community. Build your expertise.</h2>
            <p className="lead">Four tracks designed around how the industry actually works, each with a published year-long plan.</p>
          </div>
          <div className="domain-grid">
            {DOMAINS.map((d) => {
              const Icon = DOMAIN_ICONS[d.id];
              return (
                <a key={d.id} href={`#/domains/${d.id}`} className="domain-card" style={{ "--c": d.color }}>
                  <span className="domain-icon"><Icon size={22} /></span>
                  <h3>{d.community}</h3>
                  <p>{d.tagline}</p>
                  <div className="chips">{d.highlights.map((h) => <span key={h} className="chip static">{h}</span>)}</div>
                  <span className="more">See the year's plan <ArrowRight size={14} /></span>
                </a>
              );
            })}
          </div>
        </div>
      </section>

      <section className="section">
        <div className="container">
          <div className="section-head">
            <p className="eyebrow">The model</p>
            <h2>Built for scale. Designed for impact.</h2>
          </div>
          <div className="steps-grid">
            {MODEL_STEPS.map((s, i) => (
              <div key={s.title} className="step-card">
                <span className="step-num">0{i + 1}</span>
                <h3>{s.title}</h3>
                <p>{s.text}</p>
              </div>
            ))}
          </div>
          <div className="why-grid">
            {WHY.map((w) => (
              <div key={w.title}><h4>{w.title}</h4><p className="muted">{w.text}</p></div>
            ))}
          </div>
        </div>
      </section>

      <section className="section alt">
        <div className="container">
          <div className="section-head">
            <p className="eyebrow"><CalendarDays size={14} /> Annual calendar</p>
            <h2>What runs across the year</h2>
            <p className="lead">The published plan every chapter works to, quarter by quarter, ending in a cross-domain demo day.</p>
          </div>
          <div className="quarter-grid">
            {QUARTERS.map((q) => (
              <div key={q.name} className="quarter">
                <h3>{q.name}</h3>
                <p className="muted small">{q.months}</p>
                <ul>
                  {q.items.map(([dom, item]) => (
                    <li key={dom}><span className={`dot dot-${dom.split(" ")[0].toLowerCase()}`} /> <b>{dom}</b> {item}</li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="section">
        <div className="container two-col">
          <div>
            <p className="eyebrow"><MapPin size={14} /> Community chapters</p>
            <h2>Find your city</h2>
            <div className="chapter-active">
              <span className="pill live">Active</span>
              <h3>{CHAPTERS.active.city} Tech Chapter</h3>
              <p className="muted small">{CHAPTERS.active.city}, {CHAPTERS.active.state} · Chapter lead: {CHAPTERS.active.lead}</p>
              <p>{CHAPTERS.active.text}</p>
              <a className="btn ghost" href={askUrl("How do I join the Pune chapter?")}>How do I join? <ArrowRight size={14} /></a>
            </div>
            <p className="muted small planned-label">Planned chapters</p>
            <div className="chips">
              {CHAPTERS.planned.map(([c, s]) => <span key={c} className="chip static">{c} · {s}</span>)}
            </div>
          </div>
          <div>
            <p className="eyebrow"><Building2 size={14} /> Industry leaders</p>
            <h2>Guided by practitioners</h2>
            <div className="leader-grid">
              {LEADERS.map((l) => (
                <div key={l.name} className="leader">
                  <span className="avatar">{l.name.split(" ").map((p) => p[0]).join("")}</span>
                  <div><b>{l.name}</b><p className="small muted">{l.role}</p><p className="small">{l.area}</p></div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      <section className="section">
        <div className="container">
          <div className="cta">
            <div>
              <h2>Bring ISDIC to your campus</h2>
              <p>Free for students and partner colleges. The college provides the space; ISDIC brings the curriculum, mentors and community.</p>
            </div>
            <div className="cta-actions">
              <a className="btn light" href={`${SITE}/get-involved`} target="_blank" rel="noreferrer">Get involved <ExternalLink size={14} /></a>
              <a className="btn outline-light" href={askUrl("How can my college partner with ISDIC?")}>Ask how it works</a>
            </div>
          </div>
        </div>
      </section>
    </>
  );
}
