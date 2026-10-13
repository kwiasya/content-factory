import { getJson, problemOf, saveText, send } from "../api";
import type { Problem } from "../i18n";

export type VideoStatus = "idea" | "brief" | "script" | "recording" | "edit" | "review" | "published";

export type Stage = "idea" | "script" | "edit" | "done";

export interface VideoSummary {
  slug: string;
  title: string;
  format: string | null;
  channel: string | null;
  status: VideoStatus | null;
  stage: Stage | null;
  legacy: boolean;
  updated: string;
  error: string | null;
  error_code: string | null;
}

export interface HistoryEntry {
  status: VideoStatus;
  at: string;
  note?: string;
}

export interface VideoJson {
  schema: string;
  slug: string;
  title_working?: string;
  format?: string;
  channel?: string | null;
  language?: string | null;
  walks?: string[];
  status?: VideoStatus;
  history?: HistoryEntry[];
  references?: string[];
  ideas?: Array<string | number>;
  published_url?: string | null;
  legacy: boolean;
}

export type FileKind =
  | "video"
  | "script"
  | "brief"
  | "voiceover"
  | "notes"
  | "references"
  | "subtitle"
  | "render"
  | "overlay"
  | "source"
  | "other";

export interface VideoFile {
  path: string;
  kind: FileKind;
  size: number;
  mtime: string;
  editable: boolean;
  media: string | null;
}

export interface Proxy {
  walk: string;
  name: string;
  size: number;
  media: string;
}

export interface VideoDetail {
  slug: string;
  legacy: boolean;
  folder: string;
  video: VideoJson;
  hash: string | null;
  statuses: VideoStatus[];
  updated: string;
  files: VideoFile[];
  proxies: Proxy[];
}

export interface TextFile {
  path: string;
  kind: FileKind;
  format: "markdown" | "json" | "text";
  text: string;
  hash: string;
}

export interface Channel {
  id: string;
  formats: string[];
  languages: string[];
  watchlists: string[];
  videos: number;
}

export interface VideoFilter {
  format?: string;
  channel?: string;
}

export interface VideoCreate {
  title: string;
  format: string;
  channel: string;
  new_channel?: boolean;
  idea_id?: number | null;
}

export type CreateResult = { status: "created"; detail: VideoDetail } | { status: "error"; problem: Problem };

export type StatusResult =
  | { status: "saved"; detail: VideoDetail }
  | { status: "conflict" }
  | { status: "error"; problem: Problem };

const v = (slug: string) => `/api/videos/${encodeURIComponent(slug)}`;

export const videosApi = {
  list: (filter: VideoFilter = {}) => {
    const q = new URLSearchParams();
    if (filter.format) q.set("format", filter.format);
    if (filter.channel) q.set("channel", filter.channel);
    const query = q.toString();
    return getJson<{ videos: VideoSummary[] }>(`/api/videos${query ? `?${query}` : ""}`).then((r) => r.videos);
  },
  channels: () => getJson<{ channels: Channel[] }>("/api/channels").then((r) => r.channels),
  async create(body: VideoCreate): Promise<CreateResult> {
    const r = await send("/api/videos", "POST", body);
    return r.ok
      ? { status: "created", detail: r.body as unknown as VideoDetail }
      : { status: "error", problem: problemOf(r.body) };
  },
  get: (slug: string) => getJson<VideoDetail>(v(slug)),
  file: (slug: string, path: string) => getJson<TextFile>(`${v(slug)}/file?path=${encodeURIComponent(path)}`),
  saveFile: (slug: string, path: string, text: string, hash: string) =>
    saveText(`${v(slug)}/file`, "PUT", { path, text, hash }),
  async setStatus(slug: string, status: VideoStatus, note: string, hash: string): Promise<StatusResult> {
    const r = await send(`${v(slug)}/status`, "POST", { status, note, hash });
    if (r.ok) {
      return { status: "saved", detail: r.body as unknown as VideoDetail };
    }
    if (r.status === 409 && typeof r.body.hash === "string") {
      return { status: "conflict" };
    }
    return { status: "error", problem: problemOf(r.body) };
  },
};
