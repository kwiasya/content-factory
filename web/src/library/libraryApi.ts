import { getJson, sendOrThrow } from "../api";

export type Kind = "audio" | "video" | "image" | "font" | "template";
export type Rights = "own" | "free" | "unknown";

export interface Loudness {
  i: number | null;
  tp: number | null;
  lra: number | null;
  method: "loudnorm" | "padded";
}

export interface Variant {
  role: "original" | "alpha" | "still";
  path: string;
  media: string | null;
  size: number | null;
  alpha: boolean;
  codec: string | null;
  pix_fmt: string | null;
  duration_s: number | null;
  width: number | null;
  height: number | null;
}

export interface AssetCard {
  id: string;
  pack: string;
  category: string;
  category_source: "mapping" | "fallback" | "kind";
  ref: string;
  name: string;
  author_name: string | null;
  aliases: string[];
  kind: Kind;
  folder: string;
  file: { path: string; name: string; size: number | null; mtime: string | null };
  media: { original: string | null; alpha: string | null; png: string | null; poster: string | null; preview: string | null };
  duration_s: number | null;
  fps: number | null;
  width: number | null;
  height: number | null;
  has_audio: boolean;
  alpha: boolean;
  green_screen: boolean;
  loudness: Loudness | null;
  rights: Rights;
  rights_default: Rights;
  rights_override: Rights | null;
  caption: string | null;
  tags: string[];
  agent_caption: string | null;
  agent_tags: string[];
  updated_at: string | null;
  variants?: Variant[];
}

export interface PackSummary {
  id: string;
  root: string;
  indexed_at: string | null;
  index_missing: boolean;
  assets: number;
  by_category: Record<string, number>;
  fallback: number;
}

export interface LibraryInfo {
  packs: PackSummary[];
  categories: string[];
  rights: Rights[];
}

export interface TagCount {
  tag: string;
  n: number;
  author: boolean;
}

export interface AssetPage {
  assets: AssetCard[];
  total: number;
  tags: TagCount[];
}

export interface Filter {
  pack?: string;
  category?: string;
  tags?: string[];
  q?: string;
  rights?: string;
}

export type CheckResult = { ok: true; id: string; canonical: string } | { ok: false; suggestions: string[] };

export interface AuthorFields {
  caption?: string | null;
  tags?: string[] | null;
  rights?: Rights | null;
  name?: string | null;
}

function params(filter: Filter, extra: Record<string, string> = {}): string {
  const p = new URLSearchParams(extra);
  for (const key of ["pack", "category", "q", "rights"] as const) {
    const v = filter[key];
    if (v) {
      p.set(key, v);
    }
  }
  if (filter.tags?.length) {
    p.set("tags", filter.tags.join(","));
  }
  return p.toString();
}

const base = "/api/library";

export const libraryApi = {
  info: () => getJson<LibraryInfo>(base),
  assets: (filter: Filter, limit = 5000) => getJson<AssetPage>(`${base}/assets?${params(filter, { limit: String(limit) })}`),
  asset: (id: string) => getJson<{ asset: AssetCard }>(`${base}/assets/${encodeURIComponent(id)}`).then((r) => r.asset),
  setAuthor: (id: string, fields: AuthorFields) =>
    sendOrThrow<{ asset: AssetCard }>(`${base}/assets/${encodeURIComponent(id)}/author`, "PUT", fields).then((r) => r.asset),
  reveal: (id: string) => sendOrThrow<{ path: string }>(`${base}/assets/${encodeURIComponent(id)}/reveal`, "POST"),
  resolve: (ref: string) =>
    getJson<{ ref: string; canonical: string; alias: boolean; asset: AssetCard }>(
      `${base}/refs/resolve?ref=${encodeURIComponent(ref)}`,
    ),
  suggest: (q: string, limit = 20) =>
    getJson<{ suggestions: AssetCard[] }>(`${base}/refs/suggest?q=${encodeURIComponent(q)}&limit=${limit}`).then(
      (r) => r.suggestions,
    ),
  check: (refs: string[]) =>
    sendOrThrow<{ refs: Record<string, CheckResult> }>(`${base}/refs/check`, "POST", { refs }).then((r) => r.refs),
  tags: (q: string, limit = 12) =>
    getJson<{ tags: TagCount[] }>(`${base}/tags?q=${encodeURIComponent(q)}&limit=${limit}`).then((r) => r.tags),
};
