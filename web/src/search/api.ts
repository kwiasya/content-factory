import { getJson } from "../api";

export interface Snippet {
  line: number;
  text: string;
}

export interface SearchHit {
  path: string;
  title: string;
  count: number;
  snippets: Snippet[];
}

export interface SearchResult {
  q: string;
  total: number;
  truncated: boolean;
  groups: { id: string; title: string; hits: SearchHit[] }[];
}

export const searchApi = {
  search: (q: string, all: boolean) =>
    getJson<SearchResult>(`/api/search?q=${encodeURIComponent(q)}${all ? "&all=1" : ""}`),
};
