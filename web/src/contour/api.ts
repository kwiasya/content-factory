export interface Watchlist {
  name: string;
  format_id: string;
  author_channel: string | null;
  language: string;
  region: string | null;
  queries: string[];
  channel_count: number;
  created_at: string;
}

export interface ReferenceChannel {
  external_id: string;
  handle: string | null;
  title: string | null;
  subscriber_count: number | null;
  video_count: number | null;
  view_count: number | null;
  own: boolean;
  fetched_at: string | null;
}

export interface FeedRow {
  external_id: string;
  date: string | null;
  outlier: number | null;
  views: number | null;
  title: string | null;
  handle: string | null;
  url: string | null;
  analyzed: boolean;
  kind: string | null;
  duration_s: number | null;
  published_at: string | null;
  channel_title: string | null;
  likes: number | null;
  comments: number | null;
  own: boolean;
  candidate: boolean;
}

export interface FeedFilters {
  days: string;
  min_outlier: string;
  min_views: string;
  kind: string;
  max_duration: string;
  limit: string;
}

export const DEFAULT_FILTERS: FeedFilters = {
  days: "30",
  min_outlier: "",
  min_views: "",
  kind: "",
  max_duration: "",
  limit: "20",
};

export interface Span {
  start_s: number;
  end_s: number | null;
}

export interface Section extends Span {
  text: string;
}

export interface Chapter extends Span {
  title: string;
}

export interface Peak extends Span {
  value: number;
  quote: string | null;
}

export interface Measured {
  duration_s?: number | null;
  kind?: string | null;
  cut_count?: number | null;
  cuts_per_min?: number | null;
  first_shot_s?: number | null;
  first_person_s?: number | null;
  first_face_s?: number | null;
  speech_onset_s?: number | null;
  spoken_hook?: string | null;
  language?: string | null;
  first_text_s?: number | null;
  first_text?: string | null;
  sections?: Section[] | null;
  chapters?: Chapter[] | null;
  heatmap_peaks?: Peak[] | null;
  notes?: string[] | null;
}

export type Analysis = Record<string, unknown>;

export interface CardDetail {
  external_id: string;
  reference: FeedRow | null;
  card: { schema: string; measured: Measured; analysis: Analysis | null };
  sections: Section[];
  proposed: { kind: string; value: string }[];
  media: string | null;
}

export type SummaryKind = "hooks" | "formats" | "topics";

export interface Example {
  external_id: string;
  title: string | null;
  outlier: number | null;
  views: number | null;
  url: string | null;
  handle: string | null;
  date: string | null;
  spoken_hook: string | null;
  formula: string | null;
  proposed: boolean;
}

export interface Group {
  value: string;
  label: string | null;
  proposed: boolean;
  count: number;
  weight: number;
  best_outlier: number | null;
  examples: Example[];
}

export interface Uncarded {
  external_id: string;
  title: string | null;
  outlier: number | null;
  views: number | null;
  url: string | null;
  handle: string | null;
  date: string | null;
  measured: boolean;
}

export interface Summary {
  summary: SummaryKind;
  watchlist: string;
  format_id: string;
  days: number;
  since: string;
  references: number;
  carded: number;
  min_outlier: number;
  weight: string;
  sections: { kind: string; groups: Group[] }[];
  uncarded: Uncarded[];
}

export type IdeaStatus = "inbox" | "shortlisted" | "discarded" | "brief";
export type IdeaAction = "shortlist" | "discard" | "restore";

export interface Idea {
  id: number;
  watchlist: string;
  title: string;
  status: IdeaStatus;
  fields: Record<string, unknown>;
  sources: { id: number; external_id: string; title: string | null; url: string | null }[];
  notes: { at: string; text: string }[];
  brief_path: string | null;
  created_at: string;
  updated_at: string;
}

export interface Brief {
  idea: number;
  path: string;
  text: string;
  hash: string;
}

export type BriefSave =
  | { status: "saved"; hash: string }
  | { status: "conflict"; text: string; hash: string }
  | { status: "error"; message: string };

export interface TaxonomyValue {
  kind: string;
  value: string;
  status: "approved" | "proposed" | "rejected";
  source: string;
  label: string | null;
  note: string | null;
}

export interface TaxonomyChange extends TaxonomyValue {
  cards: string[];
}

export interface Quota {
  day: string;
  buckets: { bucket: string; limit: number; used: number; remaining: number }[];
  by_method: { method: string; calls: number; units: number }[];
}

export class NotFound extends Error {}

function message(detail: unknown): string {
  return typeof detail === "string" ? detail : JSON.stringify(detail);
}

async function getJson<T>(url: string): Promise<T> {
  const r = await fetch(url);
  if (!r.ok) {
    const text = await r.text();
    let detail = text;
    try {
      detail = message(JSON.parse(text).detail);
    } catch {
      detail = `${r.status} ${text || r.statusText}`;
    }
    throw r.status === 404 ? new NotFound(detail) : new Error(detail);
  }
  return (await r.json()) as T;
}

interface Sent {
  ok: boolean;
  status: number;
  body: Record<string, unknown>;
}

async function send(url: string, method: string, payload?: unknown): Promise<Sent> {
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

async function sendOrThrow<T>(url: string, method: string, payload?: unknown): Promise<T> {
  const r = await send(url, method, payload);
  if (!r.ok) {
    throw new Error(message(r.body.detail));
  }
  return r.body as unknown as T;
}

const BASE = "/api/contour";
const wl = (name: string) => `${BASE}/watchlists/${encodeURIComponent(name)}`;

function query(params: Record<string, string>): string {
  const q = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v.trim() !== "") {
      q.set(k, v.trim());
    }
  }
  const s = q.toString();
  return s ? `?${s}` : "";
}

export const mediaUrl = (path: string) => `/api/media?path=${encodeURIComponent(path)}`;

export const contourApi = {
  watchlists: () => getJson<{ watchlists: Watchlist[] }>(`${BASE}/watchlists`).then((r) => r.watchlists),
  watchlist: (name: string) => getJson<{ watchlist: Watchlist; channels: ReferenceChannel[] }>(wl(name)),
  feed: (name: string, filters: FeedFilters) =>
    getJson<{ rows: FeedRow[] }>(`${wl(name)}/feed${query({ ...filters })}`).then((r) => r.rows),
  card: (id: string) => getJson<CardDetail>(`${BASE}/cards/${encodeURIComponent(id)}`),
  summary: (name: string, what: SummaryKind, days: string) =>
    getJson<Summary>(`${wl(name)}/summary/${what}${query({ days })}`),
  ideas: (watchlist: string, status: string) =>
    getJson<{ ideas: Idea[]; statuses: IdeaStatus[] }>(`${BASE}/ideas${query({ watchlist, status })}`),
  move: (id: number, action: IdeaAction) => sendOrThrow<Idea>(`${BASE}/ideas/${id}/${action}`, "POST"),
  note: (id: number, text: string) => sendOrThrow<Idea>(`${BASE}/ideas/${id}/notes`, "PUT", { text }),
  brief: (id: number) => getJson<Brief>(`${BASE}/ideas/${id}/brief`),
  async saveBrief(id: number, text: string, hash: string): Promise<BriefSave> {
    const r = await send(`${BASE}/ideas/${id}/brief`, "PUT", { text, hash });
    if (r.ok) {
      return { status: "saved", hash: r.body.hash as string };
    }
    if (r.status === 409 && typeof r.body.hash === "string") {
      return { status: "conflict", text: r.body.text as string, hash: r.body.hash };
    }
    return { status: "error", message: message(r.body.detail) };
  },
  taxonomy: (kind: string, status: string) =>
    getJson<{ values: TaxonomyValue[]; kinds: string[]; statuses: string[] }>(
      `${BASE}/taxonomy${query({ kind, status })}`,
    ),
  judge: (kind: string, value: string, action: "approve" | "reject") =>
    sendOrThrow<TaxonomyChange>(
      `${BASE}/taxonomy/${encodeURIComponent(kind)}/${encodeURIComponent(value)}/${action}`,
      "POST",
    ),
  quota: () => getJson<Quota>(`${BASE}/quota`),
};
