import { useState, useEffect, useRef, useCallback } from "react";

// IntervalMs. Sin peticiones solapadas y en pausa con la pestaña oculta.
export function usePolling(fn, intervalMs) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);
  const fnRef = useRef(fn);
  const busy = useRef(false);
  useEffect(() => {
    fnRef.current = fn;
  });

  const run = useCallback(async () => {
    if (busy.current) return;
    busy.current = true;
    try {
      setData(await fnRef.current());
      setError(null);
    } catch (e) {
      setError(e);
    } finally {
      busy.current = false;
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let timer;
    const tick = () => {
      if (!document.hidden) run();
    };
    run();
    timer = setInterval(tick, intervalMs);
    const onVisible = () => {
      if (!document.hidden) run();
    };
    document.addEventListener("visibilitychange", onVisible);
    return () => {
      clearInterval(timer);
      document.removeEventListener("visibilitychange", onVisible);
    };
  }, [run, intervalMs]);

  return { data, error, loading, refresh: run };
}
