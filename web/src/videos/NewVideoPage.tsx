import { useEffect, useState, type FormEvent } from "react";
import { contourApi, type Idea, type Watchlist } from "../contour/api";
import { ErrorLine } from "../ErrorLine";
import { useT, type Problem } from "../i18n";
import { useDeskData } from "../shell/DeskData";
import { NEW_VIDEO_HASH } from "../shell/routes";
import { VIDEOS_PREFIX, videoHref } from "./routes";
import { videosApi } from "./videosApi";

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

  const newChannel = channel === NEW_CHANNEL;
  const channelValue = newChannel ? channelName.trim() : channel;
  const ready = title.trim() !== "" && format !== "" && channelValue !== "" && !pending;
  const bad = fieldOf(problem);

  const pickBrief = (value: string) => {
    setIdeaId(value);
    const idea = ideas.find((i) => String(i.id) === value);
    if (!idea) return;
    const w = watchlists.find((x) => x.name === idea.watchlist);
    if (!title.trim()) setTitle(idea.title);
    if (!format && w && data.formats.some((f) => f.id === w.format_id)) setFormat(w.format_id);
    if (!channel && w?.author_channel && data.channels.some((c) => c.id === w.author_channel)) {
      setChannel(w.author_channel);
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
    window.location.hash = videoHref(result.detail.slug);
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
          <input autoFocus required maxLength={200} value={title} onChange={(e) => setTitle(e.target.value)} />
        </label>
        <label className={bad === "format" ? "invalid" : ""}>
          <span>{t("newVideo.fieldFormat")}</span>
          <select required value={format} onChange={(e) => setFormat(e.target.value)}>
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
          <select required value={channel} onChange={(e) => setChannel(e.target.value)}>
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
          <select value={ideaId} disabled={briefError !== null} onChange={(e) => pickBrief(e.target.value)}>
            <option value="">{t("newVideo.noBrief")}</option>
            {ideas.map((i) => (
              <option key={i.id} value={String(i.id)}>
                #{i.id} {i.title} ({i.watchlist})
              </option>
            ))}
          </select>
          {briefError && (
            <span className="muted brief-unavailable">
              {t("newVideo.briefUnavailable")} {t.problem(briefError)}
            </span>
          )}
        </label>
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
