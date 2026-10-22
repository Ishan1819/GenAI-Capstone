export const COLORS = {
  Domain: "#2f5a4c", Module: "#4f7a45", Level: "#c08a2e", Skill: "#a4443a",
  Tool: "#3b6680", Event: "#b0562f", Partner: "#6b7a3a", Mentor: "#7a5a86",
  Chapter: "#8a7356", Location: "#9a8f80", Program: "#3d7a6e", Organization: "#5a5048",
  Member: "#6f8f9c", College: "#a07c5a", Interest: "#b38a9a",
};

export default function GraphView({ graph }) {
  const nodes = graph.nodes.slice(0, 16);
  const ids = new Set(nodes.map((n) => n.id));
  const edges = graph.edges.filter((e) => ids.has(e.source) && ids.has(e.target));
  if (!nodes.length) return <p className="muted">No graph path was used for this answer.</p>;

  const W = 620, H = 340, cx = W / 2, cy = H / 2, r = Math.min(W, H) / 2 - 50;
  const pos = {};
  nodes.forEach((n, i) => {
    const a = (2 * Math.PI * i) / nodes.length - Math.PI / 2;
    pos[n.id] = { x: cx + r * 1.3 * Math.cos(a), y: cy + r * Math.sin(a) };
  });

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="graph">
      <defs>
        <marker id="arrow" viewBox="0 0 10 10" refX="22" refY="5" markerWidth="6" markerHeight="6" orient="auto">
          <path d="M0 0L10 5L0 10z" fill="#999" />
        </marker>
      </defs>
      {edges.map((e, i) => {
        const a = pos[e.source], b = pos[e.target];
        return (
          <g key={i}>
            <line x1={a.x} y1={a.y} x2={b.x} y2={b.y} stroke="#bbb" markerEnd="url(#arrow)" />
            <text x={(a.x + b.x) / 2} y={(a.y + b.y) / 2} className="edge-label">{e.relation}</text>
          </g>
        );
      })}
      {nodes.map((n) => (
        <g key={n.id}>
          <circle cx={pos[n.id].x} cy={pos[n.id].y} r="9" fill={COLORS[n.type] || "#888"} />
          <text x={pos[n.id].x} y={pos[n.id].y - 14} className="node-label">{n.name}</text>
        </g>
      ))}
    </svg>
  );
}
