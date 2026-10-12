import { useCallback, useState } from "react";
import { contourApi, type Idea, type IdeaAction } from "./api";
import { BriefEditor } from "./BriefEditor";
import { Cmd, ContourShell, Status } from "./ContourShell";
import { cardHref, ideasHref } from "./routes";
import { useLoad } from "./useLoad";

const ACTIONS: Record<string, { action: IdeaAction; label: string }[]> = {
  inbox: [
    { action: "shortlist", label: "Shortlist" },
    { action: "discard", label: "Discard" },
  ],
  discarded: [{ action: "restore", label: "Restore" }],
};

export function IdeasPage({ selected }: { selected: number | null }) {
  const [watchlist, setWatchlist] = useState("");
  const [status, setStatus] = useState("");
  const [actionError, setActionError] = useState<string | null>(null);
  const watchlists = useLoad(contourApi.watchlists);
  const loader = useCallback(() => contourApi.ideas(watchlist, status), [watchlist, status]);
  const { data, error, reload } = useLoad(loader);

  const act = (id: number, action: IdeaAction) => {
    setActionError(null);
    contourApi.move(id, action).then(reload, (e: Error) => setActionError(e.message));
  };

  const ideas = data?.ideas ?? [];
  const current = ideas.find((i) => i.id === selected) ?? null;

  return (
    <ContourShell active="ideas">
      <h1>Ideas</h1>
      <form className="filters" onSubmit={(e) => e.preventDefault()}>
        <label>
          Watchlist
          <select value={watchlist} onChange={(e) => setWatchlist(e.target.value)}>
            <option value="">all</option>
            {(watchlists.data ?? []).map((w) => (
              <option key={w.name} value={w.name}>
                {w.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Status
          <select value={status} onChange={(e) => setStatus(e.target.value)}>
            <option value="">all</option>
            {(data?.statuses ?? ["inbox", "shortlisted", "discarded", "brief"]).map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </label>
      </form>
      <Status error={error} loading={data === null && !error} />
      {actionError && <p className="error">{actionError}</p>}
      {data && ideas.length === 0 && (
        <p className="muted">
          No Ideas{status ? ` with status ${status}` : ""}. Fill the inbox with <Cmd>/suggest-ideas</Cmd> from the
          analyzed outliers of a Watchlist.
        </p>
      )}
      {ideas.length > 0 && (
        <table className="contour-table">
          <thead>
            <tr>
              <th className="num">#</th>
              <th>Idea</th>
              <th>Watchlist</th>
              <th>Status</th>
              <th className="num">Notes</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {ideas.map((i) => (
              <tr key={i.id} className={i.id === selected ? "selected" : ""}>
                <td className="num muted">{i.id}</td>
                <td>
                  <a href={ideasHref(i.id)}>{i.title}</a>
                </td>
                <td>{i.watchlist}</td>
                <td>
                  <span className={`status-pill idea-${i.status}`}>{i.status}</span>
                </td>
                <td className="num">{i.notes.length}</td>
                <td>
                  <div className="row-actions">
                    {(ACTIONS[i.status] ?? []).map((a) => (
                      <button key={a.action} onClick={() => act(i.id, a.action)}>
                        {a.label}
                      </button>
                    ))}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {selected !== null && data && !current && (
        <p className="muted">Idea {selected} is not in this list; clear the filters to see it.</p>
      )}
      {current && <IdeaDetail key={current.id} idea={current} onChanged={reload} />}
    </ContourShell>
  );
}

function text(value: unknown): string {
  return typeof value === "string" ? value : "";
}

function IdeaDetail({ idea, onChanged }: { idea: Idea; onChanged: () => void }) {
  const [note, setNote] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const f = idea.fields;
  const format = (f.storytelling_format ?? {}) as Record<string, unknown>;
  const contrast = f.contrast_mechanism as Record<string, unknown> | null | undefined;
  const personalizations = Array.isArray(f.personalizations) ? (f.personalizations as unknown[]) : [];

  const addNote = () => {
    setSaving(true);
    setError(null);
    contourApi.note(idea.id, note).then(
      () => {
        setSaving(false);
        setNote("");
        onChanged();
      },
      (e: Error) => {
        setSaving(false);
        setError(e.message);
      },
    );
  };

  return (
    <section className="idea-detail">
      <h2>
        {idea.title} <span className={`status-pill idea-${idea.status}`}>{idea.status}</span>
      </h2>
      <dl className="facts">
        <div>
          <dt>Summary</dt>
          <dd>{text(f.summary) || "—"}</dd>
        </div>
        <div>
          <dt>Positioning</dt>
          <dd>{text(f.content_positioning) || "—"}</dd>
        </div>
        <div>
          <dt>Storytelling format</dt>
          <dd>
            <code>{text(format.category) || "—"}</code> {text(format.why)}
          </dd>
        </div>
        <div>
          <dt>Contrast</dt>
          <dd>
            {contrast
              ? `Common belief: ${text(contrast.common_belief)}. Reality: ${text(contrast.contrarian_reality)}.`
              : "none"}
          </dd>
        </div>
        <div>
          <dt>Hook alignment</dt>
          <dd>{text(f.hook_alignment) || "—"}</dd>
        </div>
        <div>
          <dt>Personalizations</dt>
          <dd>
            <ol>
              {personalizations.map((p, n) => (
                <li key={n}>{text(p)}</li>
              ))}
            </ol>
          </dd>
        </div>
        <div>
          <dt>Sources</dt>
          <dd>
            {idea.sources.map((s) => (
              <div key={s.id}>
                <a href={cardHref(s.external_id)}>{s.title || s.external_id}</a>
              </div>
            ))}
          </dd>
        </div>
      </dl>

      <h2 className="section">Notes</h2>
      {idea.notes.length === 0 ? (
        <p className="muted">No notes yet.</p>
      ) : (
        <ul className="idea-notes">
          {idea.notes.map((n) => (
            <li key={`${n.at}${n.text}`}>
              <span className="muted">{n.at.replace("T", " ").replace("Z", "")}</span> {n.text}
            </li>
          ))}
        </ul>
      )}
      <div className="note-add">
        <textarea value={note} rows={2} placeholder="Add a note to this Idea" onChange={(e) => setNote(e.target.value)} />
        <button className="primary" disabled={!note.trim() || saving} onClick={addNote}>
          {saving ? "Adding…" : "Add note"}
        </button>
      </div>
      {error && <p className="error">{error}</p>}

      <h2 className="section">Brief</h2>
      {idea.status === "brief" ? (
        <BriefEditor ideaId={idea.id} />
      ) : idea.status === "shortlisted" ? (
        <p className="muted">
          No Brief yet: <Cmd>{`python -m cf.research ideas brief ${idea.id}`}</Cmd> (or ask{" "}
          <Cmd>/suggest-ideas</Cmd>) writes it.
        </p>
      ) : (
        <p className="muted">Shortlist the Idea first; a Brief is written from a shortlisted Idea.</p>
      )}
    </section>
  );
}
