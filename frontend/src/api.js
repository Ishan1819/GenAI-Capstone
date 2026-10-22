const BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, options);
  if (!res.ok) {
    let detail = res.statusText;
    try {
      detail = (await res.json()).detail || detail;
    } catch {}
    throw new Error(detail);
  }
  return res.json();
}

const json = (body) => ({
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
});

export const api = {
  chat: (message, session_id) => request("/api/chat", json({ message, session_id })),
  learningPath: (body) => request("/api/learning-path", json(body)),
  resume: (file) => {
    const form = new FormData();
    form.append("file", file);
    return request("/api/resume", { method: "POST", body: form });
  },
  searchFilters: () => request("/api/search/filters"),
  search: (body) => request("/api/search", json(body)),
  members: () => request("/api/members"),
  recommendations: (id) => request(`/api/recommendations/${id}`),
  quiz: (body) => request("/api/quiz", json(body)),
  projects: (body) => request("/api/projects", json(body)),
};

// Admin endpoints: every call carries the admin token
export function adminApi(token) {
  const auth = (opts = {}) => ({ ...opts, headers: { ...(opts.headers || {}), "X-Admin-Token": token } });
  const get = (path) => request(`/api/admin${path}`, auth());
  const post = (path, body) => request(`/api/admin${path}`, auth(body === undefined ? { method: "POST" } : json(body)));
  return {
    verify: () => get("/verify"),
    unanswered: () => get("/unanswered"),
    answer: (id, answer) => post(`/unanswered/${id}/answer`, { answer }),
    dismiss: (id) => post(`/unanswered/${id}/dismiss`),
    insights: () => get("/insights"),
    sessionPlan: (body) => post("/session-plan", body),
  };
}
