import { useEffect, useRef, useState, type FormEvent } from "react";
import { contourApi, type Idea, type Watchlist } from "../contour/api";
import { ErrorLine } from "../ErrorLine";
import { useT, type Problem } from "../i18n";
import { useDeskData, useReloadOnMount } from "../shell/DeskData";
import { NEW_VIDEO_HASH } from "../shell/routes";
import { VIDEOS_PREFIX, videoHref } from "./routes";
import { videosApi } from "./videosApi";
import { isForeign, usePerson } from "../person";

const NEW_CHANNEL = "\u0000new";

type Field = "title" | "format" | "channel";

function fieldOf(problem: Problem | null): Field | null {
  const code = problem?.code ?? "";
  if (code.startsWith("title_")) return "title";
  if (code === "format_unknown") return "format";
  if (code.startsWith("channel_")) return "channel";
  return null;
}

function NewVideoPage() {
  const t = useT();
  const data = useDeskData();
  useReloadOnMount();
  const prefilled = useRef(new Set<Field>());
  const [title, setTitle] = useState("");
  const [format, setFormat] = useState("");
  const [channel, setChannel] = useState("");
  const [channelName, setChannelName] = useState("");
  const [ideaId, setIdeaId] = useState("");
  const [ideas, setIdeas] = useState<Idea[]>([]);
  const [watchlists, setWatchlists] = useState<Watchlist[]>([]);
  const [briefError, setBriefError] = useState<Problem | null>(null);
  const [problem, setProblem] = useState<Problem | null>(null);
  const [pending, setPending] = useState(false);

  useEffect(() => {
    contourApi.ideas("", "brief").then((r) => setIdeas(r.ideas), setBriefError);
    contourApi.watchlists().then(setWatchlists, () => setWatchlists([]));
  }, []);

  const person = usePerson();
  const videoTitle = (slug: string) => data.videos?.find((v) => v.slug === slug)?.title || slug;
  const picked = ideas.find((i) => String(i.id) === ideaId);
  const pickedVideos = (picked?.videos ?? []).filter((v) => !isForeign(v.owner, person)).map((v) => v.slug);

  const newChannel = channel === NEW_CHANNEL;
  const channelValue = newChannel ? channelName.trim() : channel;
  const ready = title.trim() !== "" && format !== "" && channelValue !== "" && !pending;
  const bad = fieldOf(problem);

  const typed = (field: Field, set: (v: string) => void) => (value: string) => {
    prefilled.current.delete(field);
    set(value);
  };

  const pickBrief = (value: string) => {
    setIdeaId(value);
    const idea = ideas.find((i) => String(i.id) === value);
    const w = idea ? watchlists.find((x) => x.name === idea.watchlist) : undefined;
    const proposed: Record<Field, string> = {
      title: idea?.title ?? "",
      format: w && data.formats.some((f) => f.id === w.format_id) ? w.format_id : "",
      channel: w?.author_channel && data.channels.some((c) => c.id === w.author_channel) ? w.author_channel : "",
    };
    const current: Record<Field, string> = { title: title.trim(), format, channel };
    const setters: Record<Field, (v: string) => void> = { title: setTitle, format: setFormat, channel: setChannel };
    for (const field of ["title", "format", "channel"] as Field[]) {
      if (current[field] !== "" && !prefilled.current.has(field)) continue;
      setters[field](proposed[field]);
      if (proposed[field]) {
        prefilled.current.add(field);
      } else {
        prefilled.current.delete(field);
      }
    }
  };

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (!ready) return;
    setPending(true);
    setProblem(null);
    const result = await videosApi.create({
      title,
      format,
      channel: channelValue,
      new_channel: newChannel,
      idea_id: ideaId ? Number(ideaId) : null,
    });
    setPending(false);
    if (result.status === "error") {
      setProblem(result.problem);
      return;
    }
    data.reload();
    window.location.hash = videoHref(result.detail.slug, "brief");
  };

  const cancel = () => {
    if (window.history.length > 1) {
      window.history.back();
    } else {
      window.location.hash = VIDEOS_PREFIX;
    }
  };

  return (
    <main className="doc new-video-page">
      <h1>{t("newVideo.title")}</h1>
      <form className="new-video-form" onSubmit={submit}>
        <label className={bad === "title" ? "invalid" : ""}>
          <span>{t("newVideo.fieldTitle")}</span>
          <input autoFocus required maxLength={200} value={title} onChange={(e) => typed("title", setTitle)(e.target.value)} />
        </label>
        <label className={bad === "format" ? "invalid" : ""}>
          <span>{t("newVideo.fieldFormat")}</span>
          <select required value={format} onChange={(e) => typed("format", setFormat)(e.target.value)}>
            <option value="">{t("newVideo.pick")}</option>
            {data.formats.map((f) => (
              <option key={f.id} value={f.id}>
                {f.title}
              </option>
            ))}
          </select>
        </label>
        <label className={bad === "channel" ? "invalid" : ""}>
          <span>{t("newVideo.fieldChannel")}</span>
          <select required value={channel} onChange={(e) => typed("channel", setChannel)(e.target.value)}>
            <option value="">{t("newVideo.pick")}</option>
            {data.channels.map((c) => (
              <option key={c.id} value={c.id}>
                {c.id}
              </option>
            ))}
            <option value={NEW_CHANNEL}>{t("newVideo.newChannel")}</option>
          </select>
        </label>
        {newChannel && (
          <label className={bad === "channel" ? "invalid" : ""}>
            <span>{t("newVideo.newChannelName")}</span>
            <input value={channelName} onChange={(e) => setChannelName(e.target.value)} />
          </label>
        )}
        <label>
          <span>{t("newVideo.fieldBrief")}</span>
          <select
            value={ideaId}
            disabled={briefError !== null}
            aria-describedby={pickedVideos.length > 0 ? "brief-has-video" : undefined}
            onChange={(e) => pickBrief(e.target.value)}
          >
            <option value="">{t("newVideo.noBrief")}</option>
            {ideas.map((i) => (
              <option key={i.id} value={String(i.id)} disabled={isForeign(i.brief_owner, person)}>
                #{i.id} {i.title} ({i.watchlist})
                {isForeign(i.brief_owner, person) ? ` — ${t("newVideo.briefElsewhere", { owner: i.brief_owner ?? "" })}` : ""}
                {i.videos?.length
                  ? ` — ${t("newVideo.briefHasVideo", {
                      videos: i.videos
                        .map((v) => (isForeign(v.owner, person) ? `${v.slug} (${v.owner})` : videoTitle(v.slug)))
                        .join(", "),
                    })}`
                  : ""}
              </option>
            ))}
          </select>
          {briefError && (
            <span className="muted brief-unavailable">
              {t("newVideo.briefUnavailable")} {t.problem(briefError)}
            </span>
          )}
        </label>
        {pickedVideos.length > 0 && (
          <p id="brief-has-video" className="muted brief-has-video">
            {t("newVideo.briefVideosNote")}{" "}
            {pickedVideos.map((slug, n) => (
              <span key={slug}>
                {n > 0 && ", "}
                <a href={videoHref(slug)}>{videoTitle(slug)}</a>
              </span>
            ))}
          </p>
        )}
        <ErrorLine error={problem} />
        <div className="toolbar">
          <button type="submit" className="primary" disabled={!ready}>
            {pending ? t("newVideo.creating") : t("newVideo.create")}
          </button>
          <button type="button" onClick={cancel}>
            {t("common.cancel")}
          </button>
        </div>
      </form>
    </main>
  );
}

export function newVideoRoute(hash: string) {
  return hash === NEW_VIDEO_HASH ? <NewVideoPage /> : null;
}
