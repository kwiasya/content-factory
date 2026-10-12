import { getJson, message, saveText, send } from "../api";

export type VideoStatus = "idea" | "brief" | "script" | "recording" | "edit" | "review" | "published";

export interface VideoSummary {
  slug: string;
  title: string;
  format: string | null;
  channel: string | null;
  status: VideoStatus | null;
  legacy: boolean;
  updated: string;
  error: string | null;
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
  ideas?: string[];
  published_url?: string | null;
  legacy: boolean;
}

export type FileKind =
  | "video"
  | "script"
  | "brief"
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

export type StatusResult =
  | { status: "saved"; detail: VideoDetail }
  | { status: "conflict" }
  | { status: "error"; message: string };

const v = (slug: string) => `/api/videos/${encodeURIComponent(slug)}`;

export const videosApi = {
  list: () => getJson<{ videos: VideoSummary[] }>("/api/videos").then((r) => r.videos),
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
    return { status: "error", message: message(r.body.detail) };
  },
};
