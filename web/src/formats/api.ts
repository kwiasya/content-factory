export interface FormatSummary {
  id: string;
  title: string;
  path: string;
  has_hook_library: boolean;
}

export interface RepoText {
  path: string;
  text: string;
}

export interface Rule {
  topic: string;
  id: string;
  rule: string;
  scope: string;
  tag: string;
  source: string;
  confidence: string;
}

export interface FormatVideo {
  slug: string;
  title: string;
  status: string | null;
  channel: string | null;
  path: string;
}

export interface Format {
  id: string;
  title: string;
  format: RepoText;
  hook_library: RepoText | null;
  topics: { topic: string; path: string | null }[];
  rules: Rule[];
  videos: FormatVideo[];
}

export interface BrokenRef {
  ref: string;
  file: string;
  line: number;
}

export interface SkillLint {
  name: string;
  missing_paths: BrokenRef[];
  missing_skills: BrokenRef[];
}

async function getJson<T>(url: string): Promise<T> {
  const r = await fetch(url);
  if (!r.ok) {
    throw new Error(`${r.status} ${await r.text()}`);
  }
  return (await r.json()) as T;
}

export const formatsApi = {
  list: () => getJson<{ formats: FormatSummary[] }>("/api/formats").then((r) => r.formats),
  get: (id: string) => getJson<Format>(`/api/formats/${encodeURIComponent(id)}`),
  lintSummary: () => getJson<{ skills: Record<string, number> }>("/api/skills/lint").then((r) => r.skills),
  lint: (name: string) => getJson<SkillLint>(`/api/skills/${encodeURIComponent(name)}/lint`),
};

const SKILL_PATH = /^\.claude\/skills\/([^/]+)\//;

export function skillOf(path: string): string | null {
  const match = SKILL_PATH.exec(path);
  return match && !match[1].startsWith("remotion-") ? match[1] : null;
}
