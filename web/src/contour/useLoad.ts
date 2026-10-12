import { useCallback, useEffect, useState } from "react";
import { NotFound } from "../api";
import type { Problem } from "../i18n";

export interface Loaded<T> {
  data: T | null;
  error: Problem | null;
  missing: boolean;
  reload: () => void;
}

export function useLoad<T>(loader: () => Promise<T>): Loaded<T> {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<Problem | null>(null);
  const [missing, setMissing] = useState(false);

  const reload = useCallback(() => {
    loader().then(
      (d) => {
        setData(d);
        setError(null);
        setMissing(false);
      },
      (e: Error) => {
        setError(e);
        setMissing(e instanceof NotFound);
      },
    );
  }, [loader]);

  useEffect(reload, [reload]);

  return { data, error, missing, reload };
}
