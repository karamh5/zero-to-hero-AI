import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError } from "../api";

interface FetchState<T> {
  data: T | null;
  error: ApiError | null;
  loading: boolean;
}

/** One fetch lifecycle for every screen, so loading, error and disconnected
 * are consistent designed states rather than per-screen improvisation. */
export function useFetch<T>(
  loader: () => Promise<T>,
  deps: unknown[],
): FetchState<T> & { retry: () => void } {
  const [state, setState] = useState<FetchState<T>>({
    data: null,
    error: null,
    loading: true,
  });
  const [attempt, setAttempt] = useState(0);
  const alive = useRef(true);

  useEffect(() => {
    alive.current = true;
    setState((previous) => ({ ...previous, loading: true, error: null }));
    loader().then(
      (data) => {
        if (alive.current) setState({ data, error: null, loading: false });
      },
      (error: unknown) => {
        if (alive.current)
          setState({
            data: null,
            error:
              error instanceof ApiError
                ? error
                : new ApiError(0, String(error)),
            loading: false,
          });
      },
    );
    return () => {
      alive.current = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, attempt]);

  const retry = useCallback(() => setAttempt((n) => n + 1), []);
  return { ...state, retry };
}
