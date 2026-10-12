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

export type TextSaveResult =
  | { status: "saved"; hash: string }
  | { status: "conflict"; text: string; hash: string }
  | { status: "invalid"; message: string; violations: string[] }
  | { status: "error"; message: string };

export type StatusResult =
  | { status: "saved"; detail: VideoDetail }
  | { status: "conflict" }
  | { status: "error"; message: string };

export class NotFound extends Error {}

async function getJson<T>(url: string): Promise<T> {
  const r = await fetch(url);
  if (r.status === 404) {
    throw new NotFound(await r.text());
  }
  if (!r.ok) {
    throw new Error(`${r.status} ${await r.text()}`);
  }
  return (await r.json()) as T;
}

function message(detail: unknown): string {
  return typeof detail === "string" ? detail : JSON.stringify(detail);
}

interface Sent {
  ok: boolean;
  status: number;
  body: Record<string, unknown>;
}

async function send(url: string, method: string, payload: unknown): Promise<Sent> {
  let r: Response;
  try {
    r = await fetch(url, { method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
  } catch (e) {
    return { ok: false, status: 0, body: { detail: (e as Error).message } };
  }
  const text = await r.text();
  try {
    return { ok: r.ok, status: r.status, body: JSON.parse(text) };
  } catch {
    return { ok: false, status: r.status, body: { detail: `${r.status} ${text || r.statusText}` } };
  }
}

const v = (slug: string) => `/api/videos/${encodeURIComponent(slug)}`;

export const mediaUrl = (path: string) => `/api/media?path=${encodeURIComponent(path)}`;

export const videosApi = {
  list: () => getJson<{ videos: VideoSummary[] }>("/api/videos").then((r) => r.videos),
  get: (slug: string) => getJson<VideoDetail>(v(slug)),
  file: (slug: string, path: string) => getJson<TextFile>(`${v(slug)}/file?path=${encodeURIComponent(path)}`),
  async saveFile(slug: string, path: string, text: string, hash: string): Promise<TextSaveResult> {
    const r = await send(`${v(slug)}/file`, "PUT", { path, text, hash });
    if (r.ok) {
      return { status: "saved", hash: r.body.hash as string };
    }
    if (r.status === 409 && typeof r.body.hash === "string") {
      return { status: "conflict", text: r.body.text as string, hash: r.body.hash };
    }
    if (r.status === 422 && Array.isArray(r.body.violations)) {
      return { status: "invalid", message: message(r.body.detail), violations: r.body.violations as string[] };
    }
    return { status: "error", message: message(r.body.detail) };
  },
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
