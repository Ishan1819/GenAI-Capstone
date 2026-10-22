import { DOMAINS, SITE } from "../../data/isdic.js";

export default function Footer() {
  return (
    <footer className="footer">
      <div className="container footer-grid">
        <div>
          <a href="#/" className="brand">
            <span className="brand-mark">IS</span>
            <span className="brand-text"><strong>ISDIC</strong><small>Community Intelligence</small></span>
          </a>
          <p className="muted small footer-about">
            An AI layer over the Industry Skill Development &amp; Innovation Cell community: campus-embedded skill
            centres across cybersecurity, AI &amp; ML, cloud &amp; DevOps and software development.
          </p>
        </div>
        <div>
          <h4>Domains</h4>
          {DOMAINS.map((d) => <a key={d.id} href={`#/domains/${d.id}`}>{d.community}</a>)}
        </div>
        <div>
          <h4>AI tools</h4>
          <a href="#/assistant">Assistant</a>
          <a href="#/search">Community search</a>
          <a href="#/path">Learning path</a>
          <a href="#/quiz">Skill quiz</a>
          <a href="#/projects">Project ideas</a>
          <a href="#/resume">Resume check</a>
          <a href="#/for-you">Recommendations</a>
        </div>
        <div>
          <h4>ISDIC</h4>
          <a href={SITE} target="_blank" rel="noreferrer">isdic.in</a>
          <a href={`${SITE}/get-involved`} target="_blank" rel="noreferrer">Get involved</a>
          <a href={`${SITE}/partner`} target="_blank" rel="noreferrer">Partner with ISDIC</a>
          <a href="mailto:contact@isdic.in">contact@isdic.in</a>
        </div>
      </div>
      <div className="container footer-note small muted">
        Capstone project prototype (PCCOE, Grp_Cap_14) built for ISDIC. Not the official ISDIC website. Programme
        content is taken from isdic.in; member and event records in Search and For You are fictional demo data.
      </div>
    </footer>
  );
}
