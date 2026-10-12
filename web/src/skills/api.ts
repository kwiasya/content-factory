import { getJson } from "../api";

export interface SkillLinks {
  name: string;
  path: string;
  paths: string[];
  catalogued: string[];
  commands: string[];
  tables: string[];
  skills: string[];
  mentioned_by: string[];
}

export const skillsApi = {
  links: (name: string) => getJson<SkillLinks>(`/api/skills/${encodeURIComponent(name)}/links`),
  map: () => getJson<{ skills: SkillLinks[] }>("/api/skills/links").then((r) => r.skills),
};
