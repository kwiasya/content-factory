export type GitState =
  | "clean"
  | "modified"
  | "added"
  | "deleted"
  | "renamed"
  | "copied"
  | "untracked"
  | "ignored"
  | "conflicted";

export interface CatalogEntry {
  path: string;
  group: string;
  title: string;
  kind: "markdown" | "json";
  editable: boolean;
  git: GitState;
  skill?: string;
  vendored?: boolean;
  description?: string | null;
  size?: number;
  mtime?: string;
}

export function ownSkill(entry: CatalogEntry): string | null {
  return entry.skill && !entry.vendored ? entry.skill : null;
}

export function ownSkillPage(entry: CatalogEntry): string | null {
  return entry.path.endsWith("/SKILL.md") ? ownSkill(entry) : null;
}

export interface CatalogGroup {
  id: string;
  title: string;
  hidden: boolean;
  empty: { glob: string; hint: string }[];
  docs: CatalogEntry[];
}

export interface Doc extends CatalogEntry {
  text: string;
  hash: string;
}

export interface Meta {
  repo: string;
  branch: string | null;
  footage_root: string;
  db_path: string;
}

export interface LogEntry {
  hash: string;
  date: string;
  author: string;
  subject: string;
}

export type SaveResult<Saved = object> =
  | ({ status: "saved"; hash: string } & Saved)
  | { status: "conflict"; text: string; hash: string }
  | { status: "invalid"; message: string; violations: string[] }
  | { status: "error"; message: string };

export class NotFound extends Error {}

export function message(detail: unknown): string {
  return typeof detail === "string" ? detail : JSON.stringify(detail);
}

export async function getJson<T>(url: string): Promise<T> {
  const r = await fetch(url);
  if (!r.ok) {
    const text = await r.text();
    let detail: string;
    try {
      detail = message(JSON.parse(text).detail);
    } catch {
      detail = `${r.status} ${text || r.statusText}`;
    }
    throw r.status === 404 ? new NotFound(detail) : new Error(detail);
  }
  return (await r.json()) as T;
}

export interface Sent {
  ok: boolean;
  status: number;
  body: Record<string, unknown>;
}

export async function send(url: string, method: string, payload?: unknown): Promise<Sent> {
  let r: Response;
  try {
    r = await fetch(url, {
      method,
      headers: payload === undefined ? undefined : { "Content-Type": "application/json" },
      body: payload === undefined ? undefined : JSON.stringify(payload),
    });
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

export async function sendOrThrow<T>(url: string, method: string, payload?: unknown): Promise<T> {
  const r = await send(url, method, payload);
  if (!r.ok) {
    throw new Error(message(r.body.detail));
  }
  return r.body as unknown as T;
}

export async function saveText<Saved = object>(
  url: string,
  method: string,
  payload: unknown,
  saved: (body: Record<string, unknown>) => Saved = () => ({}) as Saved,
): Promise<SaveResult<Saved>> {
  const r = await send(url, method, payload);
  if (r.ok) {
    return { status: "saved", hash: r.body.hash as string, ...saved(r.body) };
  }
  if (r.status === 409 && typeof r.body.hash === "string") {
    return { status: "conflict", text: r.body.text as string, hash: r.body.hash };
  }
  if (r.status === 422 && Array.isArray(r.body.violations)) {
    return { status: "invalid", message: message(r.body.detail), violations: r.body.violations as string[] };
  }
  return { status: "error", message: message(r.body.detail) };
}

export const mediaUrl = (path: string) => `/api/media?path=${encodeURIComponent(path)}`;

const q = (path: string) => `path=${encodeURIComponent(path)}`;

export const api = {
  meta: () => getJson<Meta>("/api/meta"),
  catalog: (all: boolean) =>
    getJson<{ groups: CatalogGroup[] }>(`/api/catalog${all ? "?all=1" : ""}`).then((r) => r.groups),
  doc: (path: string) => getJson<Doc>(`/api/doc?${q(path)}`),
  diff: (path: string) => getJson<{ git: GitState; diff: string }>(`/api/doc/diff?${q(path)}`),
  log: (path: string) => getJson<{ entries: LogEntry[] }>(`/api/doc/log?${q(path)}`).then((r) => r.entries),
  save: (path: string, text: string, hash: string) =>
    saveText("/api/doc", "PUT", { path, text, hash }, (body) => ({ git: body.git as GitState })),
};
