import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
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

  const reload = useCallback(() => setVersion((n) => n + 1), []);

  useEffect(() => {
    videosApi.list().then(
      (v) => {
        setVideos(v);
        setError(null);
      },
      setError,
    );
    formatsApi.list().then(setFormats, () => setFormats([]));
    videosApi.channels().then(setChannels, () => setChannels([]));
  }, [version]);

  const value = useMemo(
    () => ({ videos, formats, channels, error, version, reload }),
    [videos, formats, channels, error, version, reload],
  );
  return <Context.Provider value={value}>{children}</Context.Provider>;
}

export function useDeskData(): DeskData {
  return useContext(Context);
}
