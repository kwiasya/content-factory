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

export type SaveResult =
  | { status: "saved"; hash: string; git: GitState }
  | { status: "conflict"; text: string; hash: string }
  | { status: "error"; message: string };

export async function getJson<T>(url: string): Promise<T> {
  const r = await fetch(url);
  if (!r.ok) {
    throw new Error(`${r.status} ${await r.text()}`);
  }
  return (await r.json()) as T;
}

const q = (path: string) => `path=${encodeURIComponent(path)}`;

export const api = {
  meta: () => getJson<Meta>("/api/meta"),
  catalog: (all: boolean) =>
    getJson<{ groups: CatalogGroup[] }>(`/api/catalog${all ? "?all=1" : ""}`).then((r) => r.groups),
  doc: (path: string) => getJson<Doc>(`/api/doc?${q(path)}`),
  diff: (path: string) => getJson<{ git: GitState; diff: string }>(`/api/doc/diff?${q(path)}`),
  log: (path: string) => getJson<{ entries: LogEntry[] }>(`/api/doc/log?${q(path)}`).then((r) => r.entries),
  async save(path: string, text: string, hash: string): Promise<SaveResult> {
    const r = await fetch("/api/doc", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path, text, hash }),
    });
    const body = await r.json();
    if (r.ok) {
      return { status: "saved", hash: body.hash, git: body.git };
    }
    if (r.status === 409) {
      return { status: "conflict", text: body.text, hash: body.hash };
    }
    return { status: "error", message: typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail) };
  },
};
