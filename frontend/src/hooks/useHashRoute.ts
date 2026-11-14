import { useEffect, useState } from "react";

export type Route = "dashboard" | "map" | "analytics" | "reports" | "timeline";
export const ROUTES: { id: Route; label: string }[] = [
  { id: "dashboard", label: "Dashboard" }, { id: "map", label: "Map explorer" },
  { id: "analytics", label: "Analytics" }, { id: "reports", label: "Reports" }, { id: "timeline", label: "Timelines" },
];
const parse = (): Route => (ROUTES.find((r) => `#/${r.id}` === window.location.hash)?.id ?? "map");

export function useHashRoute(): Route {
  const [route, setRoute] = useState<Route>(parse);
  useEffect(() => {
    const on = () => setRoute(parse());
    window.addEventListener("hashchange", on);
    return () => window.removeEventListener("hashchange", on);
  }, []);
  return route;
}
