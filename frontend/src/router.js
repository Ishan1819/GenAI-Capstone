import { useEffect, useState } from "react";

const read = () => {
  const [path, query = ""] = (window.location.hash.slice(1) || "/").split("?");
  return { path, params: new URLSearchParams(query) };
};

export function useRoute() {
  const [route, setRoute] = useState(read);
  useEffect(() => {
    const onChange = () => {
      setRoute(read());
      window.scrollTo(0, 0);
    };
    window.addEventListener("hashchange", onChange);
    return () => window.removeEventListener("hashchange", onChange);
  }, []);
  return route;
}

export const go = (to) => {
  window.location.hash = to;
};

export const askUrl = (q) => `#/assistant?q=${encodeURIComponent(q)}`;
