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

async function call<T>(url: string, init?: RequestInit): Promise<T> {
  const r = await fetch(url, init);
  if (!r.ok) {
    let message = `${r.status}`;
    try {
      const body = await r.json();
      message = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    } catch {
      message = `${r.status} ${r.statusText}`;
    }
    throw new Error(message);
  }
  return (await r.json()) as T;
}

export const notesApi = {
  list(filter: { kind?: NoteKind; key?: string; all?: boolean } = {}): Promise<Note[]> {
    const params = new URLSearchParams();
    if (filter.kind) params.set("kind", filter.kind);
    if (filter.key !== undefined) params.set("key", filter.key);
    if (filter.all) params.set("all", "1");
    const query = params.toString();
    return call<{ notes: Note[] }>(`/api/notes${query ? `?${query}` : ""}`).then((r) => r.notes);
  },
  add: (kind: NoteKind, key: string, text: string) =>
    call<Note>("/api/notes", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ kind, key, text }),
    }),
  resolve: (id: number) => call<Note>(`/api/notes/${id}/resolve`, { method: "POST" }),
  remove: (id: number) => call<Note>(`/api/notes/${id}`, { method: "DELETE" }),
};
