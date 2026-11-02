import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { formatsApi, type FormatSummary } from "../formats/api";
import { videosApi, type Channel, type VideoSummary } from "../videos/videosApi";
import type { Problem } from "../i18n";

export interface DeskData {
  videos: VideoSummary[] | null;
  formats: FormatSummary[];
  channels: Channel[];
  error: Problem | null;
  version: number;
  reload: () => void;
}

const Context = createContext<DeskData>({
  videos: null,
  formats: [],
  channels: [],
  error: null,
  version: 0,
  reload: () => undefined,
});

export function DeskDataProvider({ children }: { children: ReactNode }) {
  const [videos, setVideos] = useState<VideoSummary[] | null>(null);
  const [formats, setFormats] = useState<FormatSummary[]>([]);
  const [channels, setChannels] = useState<Channel[]>([]);
  const [error, setError] = useState<Problem | null>(null);
  const [version, setVersion] = useState(0);
  const latest = useRef(0);

  const reload = useCallback(() => setVersion((n) => n + 1), []);

  useEffect(() => {
    const ticket = ++latest.current;
    const current = () => ticket === latest.current;
    videosApi.list().then(
      (v) => {
        if (current()) {
          setVideos(v);
          setError(null);
        }
      },
      (e) => current() && setError(e),
    );
    formatsApi.list().then(
      (f) => current() && setFormats(f),
      () => current() && setFormats([]),
    );
    videosApi.channels().then(
      (c) => current() && setChannels(c),
      () => current() && setChannels([]),
    );
  }, [version]);

  useEffect(() => {
    const onVisible = () => {
      if (document.visibilityState === "visible") {
        reload();
      }
    };
    window.addEventListener("focus", reload);
    window.addEventListener("hashchange", reload);
    document.addEventListener("visibilitychange", onVisible);
    return () => {
      window.removeEventListener("focus", reload);
      window.removeEventListener("hashchange", reload);
      document.removeEventListener("visibilitychange", onVisible);
    };
  }, [reload]);

  const value = useMemo(
    () => ({ videos, formats, channels, error, version, reload }),
    [videos, formats, channels, error, version, reload],
  );
  return <Context.Provider value={value}>{children}</Context.Provider>;
}

export function useDeskData(): DeskData {
  return useContext(Context);
}

export function useReloadOnMount(): void {
  const { reload } = useDeskData();
  useEffect(reload, [reload]);
}
