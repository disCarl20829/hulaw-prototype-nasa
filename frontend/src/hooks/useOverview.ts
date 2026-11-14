import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { emptyRegion, fetchOverview, overviewToRegion, resolvePeriod } from "../services/hulaw-api";
import type { DataQuery, DataStatus, MascotMood, Region } from "../types";

export interface DataLocation { id: string; name: string; latitude: number; longitude: number }
interface Loaded { region: Region; mood: MascotMood }

/** Loads the drought overview for one point from the backend. Results are kept in memory per location for the session. */
export function useOverview(location: DataLocation, query: DataQuery = {}) {
  const cache = useRef(new Map<string, Loaded>());
  const [attempt, setAttempt] = useState(0);
  const forceRefresh = useRef(false);
  const [state, setState] = useState<{ key: string; status: DataStatus; error: string | null; data: Loaded | null }>({ key: "", status: "loading", error: null, data: null });
  const period = resolvePeriod(query);
  const key = `${location.id}:${location.latitude.toFixed(4)}:${location.longitude.toFixed(4)}:${period.endMonth}:${period.baselineStart}-${period.baselineEnd}`;

  useEffect(() => {
    const refresh = forceRefresh.current;
    forceRefresh.current = false;
    const hit = refresh ? undefined : cache.current.get(key);
    if (hit) { setState({ key, status: "ready", error: null, data: hit }); return; }
    const controller = new AbortController();
    setState({ key, status: "loading", error: null, data: null });
    fetchOverview(location.latitude, location.longitude, { query, refresh, signal: controller.signal })
      .then((response) => {
        const data: Loaded = { region: overviewToRegion(response, location.id, location.name), mood: response.latest.mood };
        cache.current.set(key, data);
        setState({ key, status: "ready", error: null, data });
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted) return;
        setState({ key, status: "error", error: error instanceof Error ? error.message : "Unexpected error while loading data.", data: null });
      });
    return () => controller.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key, attempt]);

  /** Retry after an error, or pass true to make the backend fetch from NASA again. */
  const reload = useCallback((refresh = false) => { forceRefresh.current = refresh; setAttempt((n) => n + 1); }, []);

  const current = state.key === key ? state : { key, status: "loading" as DataStatus, error: null, data: null };
  // Stable placeholder (no values) while loading or after an error.
  const placeholder = useMemo(() => emptyRegion(location.id, location.name, period.endMonth), [location.id, location.name, period.endMonth]);
  return {
    region: current.data?.region ?? placeholder,
    mood: current.data?.mood ?? ("default" as MascotMood),
    status: current.status, error: current.error, reload,
  };
}
