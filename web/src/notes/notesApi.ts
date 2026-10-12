import { getJson, sendOrThrow } from "../api";

export const NOTE_KINDS = ["document", "skill", "video", "card", "idea", "general"] as const;

export type NoteKind = (typeof NOTE_KINDS)[number];

export interface Note {
  id: number;
  kind: NoteKind;
  key: string;
  text: string;
  created_at: string;
  resolved_at: string | null;
}

export const notesApi = {
  list(filter: { kind?: NoteKind; key?: string; all?: boolean } = {}): Promise<Note[]> {
    const params = new URLSearchParams();
    if (filter.kind) params.set("kind", filter.kind);
    if (filter.key !== undefined) params.set("key", filter.key);
    if (filter.all) params.set("all", "1");
    const query = params.toString();
    return getJson<{ notes: Note[] }>(`/api/notes${query ? `?${query}` : ""}`).then((r) => r.notes);
  },
  add: (kind: NoteKind, key: string, text: string) => sendOrThrow<Note>("/api/notes", "POST", { kind, key, text }),
  resolve: (id: number) => sendOrThrow<Note>(`/api/notes/${id}/resolve`, "POST"),
  remove: (id: number) => sendOrThrow<Note>(`/api/notes/${id}`, "DELETE"),
};
