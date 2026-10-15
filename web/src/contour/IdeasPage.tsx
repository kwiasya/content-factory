import { useCallback, useState } from "react";
import { contourApi, type Idea, type IdeaAction } from "./api";
import { BriefEditor } from "./BriefEditor";
import { Cmd, ContourShell, Status } from "./ContourShell";
import { NoteBox } from "../notes/NoteBox";
import { cardHref, ideasHref } from "./routes";
import { useLoad } from "./useLoad";
import { useT, type Problem } from "../i18n";
import { ErrorLine } from "../ErrorLine";
import { formatTime } from "../format";
import { useDeskData } from "../shell/DeskData";
import { videoHref } from "../videos/routes";
import { isForeign, usePerson } from "../person";

const ACTIONS: Record<string, IdeaAction[]> = {
  inbox: ["shortlist", "discard"],
  discarded: ["restore"],
};

export function IdeasPage({ selected }: { selected: number | null }) {
  const t = useT();
  const [watchlist, setWatchlist] = useState("");
  const [status, setStatus] = useState("");
  const [actionError, setActionError] = useState<Problem | null>(null);
  const watchlists = useLoad(contourApi.watchlists);
  const loader = useCallback(() => contourApi.ideas(watchlist, status), [watchlist, status]);
  const { data, error, reload } = useLoad(loader);

  const act = (id: number, action: IdeaAction) => {
    setActionError(null);
    contourApi.move(id, action).then(reload, setActionError);
  };

  const ideas = data?.ideas ?? [];
  const current = ideas.find((i) => i.id === selected) ?? null;

  return (
    <ContourShell active="ideas">
      <h1>{t("ideas.title")}</h1>
      <form className="filters" onSubmit={(e) => e.preventDefault()}>
        <label>
          {t("ideas.watchlist")}
          <select value={watchlist} onChange={(e) => setWatchlist(e.target.value)}>
            <option value="">{t("common.all")}</option>
            {(watchlists.data ?? []).map((w) => (
              <option key={w.name} value={w.name}>
                {w.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          {t("ideas.status")}
          <select value={status} onChange={(e) => setStatus(e.target.value)}>
            <option value="">{t("common.all")}</option>
            {(data?.statuses ?? ["inbox", "shortlisted", "discarded", "brief"]).map((s) => (
              <option key={s} value={s}>
                {t.or(`ideas.status.${s}`, s)}
              </option>
            ))}
          </select>
        </label>
      </form>
      <Status error={error} loading={data === null && !error} />
      <ErrorLine error={actionError} />
      {data && ideas.length === 0 && (
        <p className="muted">
          {status
            ? t.rich("ideas.emptyStatus", {
                status: t.or(`ideas.status.${status}`, status),
                cmd: <Cmd>/suggest-ideas</Cmd>,
              })
            : t.rich("ideas.empty", { cmd: <Cmd>/suggest-ideas</Cmd> })}
        </p>
      )}
      {ideas.length > 0 && (
        <table className="contour-table">
          <thead>
            <tr>
              <th className="num">{t("research.col.number")}</th>
              <th>{t("ideas.col.idea")}</th>
              <th>{t("ideas.watchlist")}</th>
              <th>{t("ideas.status")}</th>
              <th className="num">{t("ideas.col.notes")}</th>
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
                  <span className={`status-pill idea-${i.status}`}>{t.or(`ideas.status.${i.status}`, i.status)}</span>
                </td>
                <td className="num">{i.notes.length}</td>
                <td>
                  <div className="row-actions">
                    {(ACTIONS[i.status] ?? []).map((a) => (
                      <button key={a} onClick={() => act(i.id, a)}>
                        {t(`ideas.action.${a}`)}
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
        <p className="muted">{t("ideas.notInList", { id: selected })}</p>
      )}
      {current && <IdeaDetail key={current.id} idea={current} onChanged={reload} />}
    </ContourShell>
  );
}

function text(value: unknown): string {
  return typeof value === "string" ? value : "";
}

function IdeaDetail({ idea, onChanged }: { idea: Idea; onChanged: () => void }) {
  const { videos } = useDeskData();
  const person = usePerson();
  const t = useT();
  const [note, setNote] = useState("");
  const [error, setError] = useState<Problem | null>(null);
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
        setError(e);
      },
    );
  };

  return (
    <section className="idea-detail">
      <h2>
        {idea.title}{" "}
        <span className={`status-pill idea-${idea.status}`}>{t.or(`ideas.status.${idea.status}`, idea.status)}</span>
      </h2>
      <dl className="facts">
        <div>
          <dt>{t("ideas.summary")}</dt>
          <dd>{text(f.summary) || "—"}</dd>
        </div>
        <div>
          <dt>{t("ideas.positioning")}</dt>
          <dd>{text(f.content_positioning) || "—"}</dd>
        </div>
        <div>
          <dt>{t("ideas.storytelling")}</dt>
          <dd>
            <code>{text(format.category) || "—"}</code> {text(format.why)}
          </dd>
        </div>
        <div>
          <dt>{t("ideas.contrast")}</dt>
          <dd>
            {contrast
              ? t("ideas.contrastText", {
                  belief: text(contrast.common_belief),
                  reality: text(contrast.contrarian_reality),
                })
              : t("common.none")}
          </dd>
        </div>
        <div>
          <dt>{t("ideas.hookAlignment")}</dt>
          <dd>{text(f.hook_alignment) || "—"}</dd>
        </div>
        <div>
          <dt>{t("ideas.personalizations")}</dt>
          <dd>
            <ol>
              {personalizations.map((p, n) => (
                <li key={n}>{text(p)}</li>
              ))}
            </ol>
          </dd>
        </div>
        <div>
          <dt>{t("ideas.sources")}</dt>
          <dd>
            {idea.sources.map((s) => (
              <div key={s.id}>
                <a href={cardHref(s.external_id)}>{s.title || s.external_id}</a>
              </div>
            ))}
          </dd>
        </div>
        <div>
          <dt>{t("ideas.videos")}</dt>
          <dd>
            {(idea.videos ?? []).length === 0 ? (
              <span className="muted">{t("ideas.noVideos")}</span>
            ) : (
              (idea.videos ?? []).map(({ slug, owner }) => (
                <div key={`${owner}/${slug}`}>
                  {isForeign(owner, person) ? (
                    <span>{t("ideas.videoElsewhere", { slug, owner })}</span>
                  ) : (
                    <a href={videoHref(slug)}>{videos?.find((v) => v.slug === slug)?.title || slug}</a>
                  )}
                </div>
              ))
            )}
          </dd>
        </div>
      </dl>

      <h2 className="section">{t("ideas.notes")}</h2>
      {idea.notes.length === 0 ? (
        <p className="muted">{t("ideas.noNotes")}</p>
      ) : (
        <ul className="idea-notes">
          {idea.notes.map((n) => (
            <li key={`${n.at}${n.text}`}>
              <span className="muted">{formatTime(n.at, t)}</span> {n.text}
            </li>
          ))}
        </ul>
      )}
      <div className="note-add">
        <textarea value={note} rows={2} placeholder={t("ideas.notePlaceholder")} onChange={(e) => setNote(e.target.value)} />
        <button className="primary" disabled={!note.trim() || saving} onClick={addNote}>
          {saving ? t("ideas.adding") : t("ideas.addNote")}
        </button>
      </div>
      <ErrorLine error={error} />

      <h2 className="section">{t("ideas.brief")}</h2>
      {idea.status === "brief" && isForeign(idea.brief_owner, person) ? (
        <p className="muted">{t("ideas.briefElsewhere", { owner: idea.brief_owner ?? "" })}</p>
      ) : idea.status === "brief" && idea.brief_owner && person.state === "loading" ? (
        <p className="muted">{t("common.loading")}</p>
      ) : idea.status === "brief" ? (
        <BriefEditor ideaId={idea.id} />
      ) : idea.status === "shortlisted" ? (
        <p className="muted">
          {t.rich("ideas.noBrief", {
            cmd: <Cmd>{`python -m cf.research ideas brief ${idea.id}`}</Cmd>,
            skill: <Cmd>/suggest-ideas</Cmd>,
          })}
        </p>
      ) : (
        <p className="muted">{t("ideas.shortlistFirst")}</p>
      )}
      <NoteBox kind="idea" noteKey={String(idea.id)} />
    </section>
  );
}
