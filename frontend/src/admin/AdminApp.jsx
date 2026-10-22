import { useMemo, useState } from "react";
import { BarChart3, ClipboardList, LogOut, MessageSquareWarning, Network } from "lucide-react";
import { adminApi } from "../api.js";
import Overview from "./Overview.jsx";
import Queue from "./Queue.jsx";
import SessionPlanner from "./SessionPlanner.jsx";
import GraphExplorer from "./GraphExplorer.jsx";

const KEY = "isdic-admin-token";
const store = {
  get: () => { try { return sessionStorage.getItem(KEY) || ""; } catch { return ""; } },
  set: (v) => { try { v ? sessionStorage.setItem(KEY, v) : sessionStorage.removeItem(KEY); } catch {} },
};

const SECTIONS = [
  { to: "/admin", label: "Overview", icon: BarChart3, view: Overview },
  { to: "/admin/questions", label: "Unanswered questions", icon: MessageSquareWarning, view: Queue },
  { to: "/admin/session-planner", label: "Session planner", icon: ClipboardList, view: SessionPlanner },
  { to: "/admin/graph", label: "Knowledge graph", icon: Network, view: GraphExplorer },
];

function Login({ onLogin }) {
  const [token, setToken] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await adminApi(token).verify();
      onLogin(token);
    } catch (err) {
      setError(err.message === "Invalid admin token" ? "That token is not valid." : err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="admin-login">
      <form className="panel stack" onSubmit={submit}>
        <a href="#/" className="brand">
          <span className="brand-mark">is</span>
          <span className="brand-text"><strong>ISDIC</strong><small>Admin console</small></span>
        </a>
        <p className="muted">For the ISDIC team and chapter leads. Enter the admin token from the backend's <code>.env</code>.</p>
        <label>Admin token<input type="password" value={token} onChange={(e) => setToken(e.target.value)} autoFocus /></label>
        {error && <p className="error">{error}</p>}
        <button disabled={busy || !token}>{busy ? "Checking…" : "Sign in"}</button>
        <a href="#/" className="small muted">← Back to the member portal</a>
      </form>
    </div>
  );
}

export default function AdminApp({ path }) {
  const [token, setToken] = useState(store.get);
  const api = useMemo(() => adminApi(token), [token]);
  const login = (t) => { store.set(t); setToken(t); };
  const logout = () => { store.set(""); setToken(""); };

  if (!token) return <Login onLogin={login} />;
  const section = SECTIONS.find((s) => s.to === path) || SECTIONS[0];
  const View = section.view;

  return (
    <div className="admin-shell">
      <aside className="admin-side">
        <a href="#/admin" className="brand">
          <span className="brand-mark">is</span>
          <span className="brand-text"><strong>ISDIC</strong><small>Admin console</small></span>
        </a>
        <nav>
          {SECTIONS.map(({ to, label, icon: Icon }) => (
            <a key={to} href={`#${to}`} className={section.to === to ? "active" : ""}><Icon size={17} /> {label}</a>
          ))}
        </nav>
        <div className="admin-side-foot">
          <a href="#/">View member portal</a>
          <button className="secondary" onClick={logout}><LogOut size={15} /> Sign out</button>
        </div>
      </aside>
      <main className="admin-main">
        <h1>{section.label}</h1>
        <View api={api} onAuthError={logout} />
      </main>
    </div>
  );
}
