import { useState } from "react";
import { ChevronDown, Menu, X } from "lucide-react";

const LEARN = [
  { to: "/path", label: "Learning Path", text: "A roadmap in prerequisite order" },
  { to: "/quiz", label: "Skill Quiz", text: "Test yourself at your level" },
  { to: "/projects", label: "Project Ideas", text: "Portfolio projects that fit you" },
  { to: "/resume", label: "Resume Check", text: "Find your domain and level" },
];

export default function Navbar({ path }) {
  const [open, setOpen] = useState(false);
  const active = (to) => (to === "/" ? path === "/" : path.startsWith(to));
  const link = (to, label) => (
    <a key={to} href={`#${to}`} className={active(to) ? "active" : ""} onClick={() => setOpen(false)}>{label}</a>
  );
  return (
    <header className="nav">
      <div className="container nav-inner">
        <a href="#/" className="brand" onClick={() => setOpen(false)}>
          <span className="brand-mark">is</span>
          <span className="brand-text">
            <strong>ISDIC</strong>
            <small>Community Intelligence</small>
          </span>
        </a>
        <nav className={`nav-links ${open ? "open" : ""}`}>
          {link("/", "Home")}
          {link("/assistant", "Assistant")}
          {link("/search", "Search")}
          <div className="nav-menu">
            <span className={`nav-menu-label ${LEARN.some((l) => active(l.to)) ? "active" : ""}`}>
              Learn <ChevronDown size={14} />
            </span>
            <div className="nav-dropdown">
              {LEARN.map((l) => (
                <a key={l.to} href={`#${l.to}`} className={active(l.to) ? "active" : ""} onClick={() => setOpen(false)}>
                  <b>{l.label}</b><small>{l.text}</small>
                </a>
              ))}
            </div>
          </div>
          {link("/for-you", "For You")}
        </nav>
        <button className="icon-btn nav-toggle" aria-label="Menu" onClick={() => setOpen(!open)}>
          {open ? <X size={20} /> : <Menu size={20} />}
        </button>
      </div>
    </header>
  );
}
