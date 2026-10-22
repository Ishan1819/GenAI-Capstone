import { useEffect, useMemo, useState } from "react";
import { Crosshair, RotateCcw, Search } from "lucide-react";
import { COLORS } from "../components/GraphView.jsx";

const W = 900, H = 600;

// Small force-directed layout (repulsion + spring edges + gravity); fine for ~150 nodes.
function layout(nodes, edges) {
  const n = nodes.length;
  const idx = new Map(nodes.map((d, i) => [d.id, i]));
  const p = nodes.map((_, i) => {
    const a = (2 * Math.PI * i) / Math.max(n, 1);
    return { x: W / 2 + 220 * Math.cos(a), y: H / 2 + 180 * Math.sin(a), vx: 0, vy: 0 };
  });
  const links = edges.map((e) => [idx.get(e.source), idx.get(e.target)]).filter(([a, b]) => a !== undefined && b !== undefined);
  for (let it = 0, t = 1; it < 300; it++, t *= 0.985) {
    for (let i = 0; i < n; i++) {
      for (let j = i + 1; j < n; j++) {
        let dx = p[i].x - p[j].x, dy = p[i].y - p[j].y;
        const d2 = Math.max(dx * dx + dy * dy, 25);
        const f = 2200 / d2;
        dx *= f / Math.sqrt(d2); dy *= f / Math.sqrt(d2);
        p[i].vx += dx; p[i].vy += dy; p[j].vx -= dx; p[j].vy -= dy;
      }
    }
    for (const [a, b] of links) {
      const dx = p[b].x - p[a].x, dy = p[b].y - p[a].y;
      const d = Math.sqrt(dx * dx + dy * dy) || 1;
      const f = (d - 70) * 0.02;
      p[a].vx += (dx / d) * f; p[a].vy += (dy / d) * f; p[b].vx -= (dx / d) * f; p[b].vy -= (dy / d) * f;
    }
    for (const q of p) {
      q.vx += (W / 2 - q.x) * 0.004; q.vy += (H / 2 - q.y) * 0.004;
      q.x += Math.max(-20, Math.min(20, q.vx * t)); q.y += Math.max(-20, Math.min(20, q.vy * t));
      q.vx *= 0.6; q.vy *= 0.6;
    }
  }
  return new Map(nodes.map((d, i) => [d.id, p[i]]));
}

export default function GraphExplorer({ api }) {
  const [graph, setGraph] = useState(null);
  const [focus, setFocus] = useState("");
  const [types, setTypes] = useState([]);
  const [selected, setSelected] = useState(null);
  const [query, setQuery] = useState("");
  const [hits, setHits] = useState([]);
  const [error, setError] = useState("");

  async function load(f = focus, t = types) {
    setError("");
    try {
      setGraph(await api.graph(f, t));
    } catch (e) {
      setError(e.message);
    }
  }
  useEffect(() => { load(); }, []);

  async function select(id) {
    try {
      setSelected(await api.node(id));
    } catch (e) {
      setError(e.message);
    }
  }

  function focusOn(id) {
    setFocus(id);
    setHits([]);
    load(id, types);
    select(id);
  }

  function toggleType(t) {
    const next = types.includes(t) ? types.filter((x) => x !== t) : [...types, t];
    setTypes(next);
    load(focus, next);
  }

  async function find(e) {
    e.preventDefault();
    if (!query.trim()) return;
    try {
      setHits(await api.find(query.trim()));
    } catch (err) {
      setError(err.message);
    }
  }

  const pos = useMemo(() => (graph ? layout(graph.nodes, graph.edges) : new Map()), [graph]);
  const allTypes = graph ? Object.keys(graph.stats.by_type).sort() : [];
  const maxDeg = graph ? Math.max(1, ...graph.nodes.map((n) => n.degree)) : 1;
  const neighbours = useMemo(() => {
    if (!selected || !graph) return new Set();
    const s = new Set([selected.id]);
    graph.edges.forEach((e) => { if (e.source === selected.id) s.add(e.target); if (e.target === selected.id) s.add(e.source); });
    return s;
  }, [selected, graph]);

  return (
    <div>
      <p className="muted">Everything the platform knows, as entities and relationships extracted from isdic.in plus community records. Click a node to inspect it; focus to explore its neighbourhood.</p>
      <div className="panel graph-toolbar">
        <form className="row" onSubmit={find}>
          <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Find an entity, e.g. Kubernetes, Pune, CTF" />
          <button><Search size={16} /> Find</button>
          <button type="button" className="secondary" onClick={() => { setFocus(""); setSelected(null); load("", types); }}><RotateCcw size={16} /> Overview</button>
        </form>
        {hits.length > 0 && (
          <div className="chips">{hits.map((h) => <button key={h.id} className="chip" onClick={() => focusOn(h.id)}>{h.name} <span className="muted">· {h.type}</span></button>)}</div>
        )}
        <div className="chips type-filter">
          {allTypes.map((t) => (
            <button key={t} className={`chip ${types.includes(t) ? "on" : ""}`} onClick={() => toggleType(t)}>
              <span className="swatch" style={{ background: COLORS[t] || "#888" }} /> {t} <span className="muted">{graph.stats.by_type[t]}</span>
            </button>
          ))}
        </div>
      </div>
      {error && <p className="error">{error}</p>}

      {graph && (
        <div className="explorer">
          <div className="card explorer-canvas">
            <p className="small muted">
              {focus ? <>Neighbourhood of <b>{graph.nodes.find((n) => n.id === focus)?.name || focus}</b></> : "Best-connected entities"}
              {" · "}{graph.nodes.length} nodes, {graph.edges.length} edges (of {graph.stats.nodes} / {graph.stats.edges})
            </p>
            {graph.nodes.length === 0 ? <p className="muted">The graph is empty. Run build_kb and generate_demo_data.</p> : (
              <svg viewBox={`0 0 ${W} ${H}`} className="explorer-svg">
                {graph.edges.map((e, i) => {
                  const a = pos.get(e.source), b = pos.get(e.target);
                  const hot = selected && (e.source === selected.id || e.target === selected.id);
                  return a && b && (
                    <g key={i} className={hot ? "hot" : selected ? "dim" : ""}>
                      <line x1={a.x} y1={a.y} x2={b.x} y2={b.y} className="ex-edge" />
                      {hot && <text x={(a.x + b.x) / 2} y={(a.y + b.y) / 2} className="ex-edge-label">{e.relation}</text>}
                    </g>
                  );
                })}
                {graph.nodes.map((n) => {
                  const q = pos.get(n.id);
                  const r = 5 + 9 * Math.sqrt(n.degree / maxDeg);
                  const dim = selected && !neighbours.has(n.id);
                  return (
                    <g key={n.id} className={`ex-node ${dim ? "dim" : ""} ${selected?.id === n.id ? "sel" : ""}`} onClick={() => select(n.id)}>
                      <circle cx={q.x} cy={q.y} r={r} fill={COLORS[n.type] || "#888"} />
                      {(r > 8 || neighbours.has(n.id)) && <text x={q.x} y={q.y - r - 4} className="ex-label">{n.name}</text>}
                    </g>
                  );
                })}
              </svg>
            )}
          </div>
          <aside className="card explorer-side">
            {!selected ? <p className="muted">Select a node to see its relationships.</p> : (
              <>
                <span className="badge" style={{ color: COLORS[selected.type] }}>{selected.type}</span>
                <h3>{selected.name}</h3>
                <p className="small muted">{selected.degree} connections · found in {selected.sources} source chunk(s)</p>
                <button className="secondary small-btn" onClick={() => focusOn(selected.id)}><Crosshair size={14} /> Focus here</button>
                {[["outgoing", "→"], ["incoming", "←"]].map(([dir, arrow]) =>
                  Object.entries(selected[dir]).map(([rel, list]) => (
                    <div key={dir + rel} className="rel-group">
                      <p className="small"><b>{arrow} {rel}</b> <span className="muted">({list.length})</span></p>
                      <div className="chips">
                        {list.slice(0, 12).map((x) => <button key={x.id} className="chip" onClick={() => select(x.id)}>{x.name}</button>)}
                        {list.length > 12 && <span className="small muted">+{list.length - 12} more</span>}
                      </div>
                    </div>
                  )))}
              </>
            )}
          </aside>
        </div>
      )}
    </div>
  );
}
