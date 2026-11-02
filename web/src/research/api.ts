import { getJson } from "../api";

export interface Topic {
  id: string;
  number: string;
  slug: string;
  title: string;
  status: string;
  chatgpt: boolean;
  result_a: boolean;
  rules: boolean;
  verification: boolean;
  notes: string[];
  docs: string[];
}

export interface Research {
  topics: Topic[];
  synthesis: string[];
  readme: string | null;
}

export const researchApi = {
  research: () => getJson<Research>("/api/research"),
};
