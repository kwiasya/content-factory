import { useEffect, useState } from "react";
import { CONTOUR_PREFIX, parseContour } from "../contour/routes";
import { FORMATS_PREFIX, parseFormats } from "../formats/FormatsRoute";
import { ErrorLine } from "../ErrorLine";
import { LangSwitch, useT } from "../i18n";
import { NOTES_HASH } from "../notes/NotesPage";
import { parseResearch } from "../research/ResearchPage";
import { SEARCH_PREFIX, SearchBox } from "../search/SearchPage";
import { VIDEOS_PREFIX, parseVideos, videoHref } from "../videos/routes";
import { videosApi, type VideoFilter, type VideoSummary } from "../videos/videosApi";
import { useDeskData } from "./DeskData";
import { AGENT_HASH, LIBRARY_HASH, NEW_VIDEO_HASH, parseDoc, parseLibrary } from "./routes";
import "./shell.css";

const FILTER_KEY = "desk.videoFilter";

function storedFilter(): VideoFilter {
  try {
    const raw = window.localStorage.getItem(FILTER_KEY);
    const parsed = raw ? JSON.parse(raw) : {};
    return {
      format: typeof parsed?.format === "string" ? parsed.format : "",
      channel: typeof parsed?.channel === "string" ? parsed.channel : "",
    };
  } catch {
    return { format: "", channel: "" };
  }
}

function storeFilter(filter: VideoFilter): void {
  try {
    window.localStorage.setItem(FILTER_KEY, JSON.stringify(filter));
  } catch {
    return;
  }
}

export const isAgent = (hash: string) => hash === AGENT_HASH || parseDoc(hash) !== null || parseResearch(hash) !== null;

const OWN_PAGES = [NEW_VIDEO_HASH, NOTES_HASH];

function isVideosTable(hash: string): boolean {
  const videos = parseVideos(hash);
  if (videos) {
    return videos.slug === null;
  }
  return !(
    OWN_PAGES.includes(hash) ||
    hash.startsWith(SEARCH_PREFIX) ||
    parseContour(hash) !== null ||
    parseFormats(hash) !== null ||
    parseLibrary(hash) !== null ||
    isAgent(hash)
  );
}

function current(active: boolean, exact: boolean): "page" | "true" | undefined {
  return active ? (exact ? "page" : "true") : undefined;
}

function NavLink({ href, hash, active, label }: { href: string; hash: string; active: boolean; label: string }) {
  return (
    <a href={href} className={active ? "active" : ""} aria-current={current(active, hash === href)}>
      <span className="name">{label}</span>
    </a>
  );
}

function VideoItem({ video, active }: { video: VideoSummary; active: boolean }) {
  const t = useT();
  const stage = video.stage ?? "none";
  const status = video.status ? t.or(`videos.status.${video.status}`, video.status) : t("stage.none");
  const tip = video.error ? t.problem({ message: video.error, code: video.error_code ?? undefined }) : video.title;
  return (
    <li>
      <a
        href={videoHref(video.slug)}
        className={active ? "active" : ""}
        aria-current={active ? "page" : undefined}
        title={tip}
      >
        <span className={`stage-dot stage-${stage}`} role="img" title={status} aria-label={status} />
        <span className="name">{video.title}</span>
        {video.legacy && (
          <span className="legacy-mark" title={t("videos.legacy")}>
            <span aria-hidden="true">L</span>
            <span className="sr-only">{t("videos.legacy")}</span>
          </span>
        )}
        {video.error && (
          <span className="error-mark" title={tip}>
            <span aria-hidden="true">!</span>
            <span className="sr-only">{tip}</span>
          </span>
        )}
      </a>
    </li>
  );
}

export function Sidebar({ hash }: { hash: string }) {
  const t = useT();
  const data = useDeskData();
  const [filter, setFilter] = useState<VideoFilter>(storedFilter);
  const [filtered, setFiltered] = useState<VideoSummary[] | null>(null);
  const filtering = Boolean(filter.format || filter.channel);
  const current = parseVideos(hash)?.slug ?? null;

  useEffect(() => {
    if (!filtering) {
      return;
    }
    let live = true;
    videosApi.list(filter).then(
      (v) => live && setFiltered(v),
      () => live && setFiltered([]),
    );
    return () => {
      live = false;
    };
  }, [filter, filtering, data.version]);

  const change = (next: VideoFilter) => {
    setFilter(next);
    storeFilter(next);
  };

  const videos = filtering ? filtered : data.videos;
  const formatIds = [...new Set([...data.formats.map((f) => f.id), ...(filter.format ? [filter.format] : [])])];
  const channelIds = [...new Set([...data.channels.map((c) => c.id), ...(filter.channel ? [filter.channel] : [])])];
  const formatTitle = (id: string) => data.formats.find((f) => f.id === id)?.title ?? id;

  return (
    <aside className="sidebar shell-sidebar">
      <div className="shell-top">
        <a
          href={NEW_VIDEO_HASH}
          className={hash === NEW_VIDEO_HASH ? "new-video active" : "new-video"}
          aria-current={hash === NEW_VIDEO_HASH ? "page" : undefined}
        >
          {t("nav.newVideo")}
        </a>
        <SearchBox />
      </div>
      <nav className="shell-nav" aria-label={t("nav.label")}>
        <div className="shell-middle">
          <section className="group">
            <h2>{t("nav.tools")}</h2>
            <ul>
              <li>
                <NavLink href={CONTOUR_PREFIX} hash={hash} active={parseContour(hash) !== null} label={t("nav.research")} />
              </li>
              <li>
                <NavLink href={FORMATS_PREFIX} hash={hash} active={parseFormats(hash) !== null} label={t("nav.formats")} />
              </li>
              <li>
                <NavLink href={LIBRARY_HASH} hash={hash} active={parseLibrary(hash) !== null} label={t("nav.library")} />
              </li>
              <li>
                <NavLink href={NOTES_HASH} hash={hash} active={hash === NOTES_HASH} label={t("nav.notes")} />
              </li>
            </ul>
          </section>
          <section className="group shell-videos">
            <h2>
              <a
                href={VIDEOS_PREFIX}
                className={isVideosTable(hash) ? "active" : ""}
                aria-current={isVideosTable(hash) ? "page" : undefined}
              >
                {t("sidebar.videos")}
              </a>
            </h2>
            <div className="video-filters">
              <select
                aria-label={t("sidebar.filterFormat")}
                title={t("sidebar.filterFormat")}
                value={filter.format ?? ""}
                onChange={(e) => change({ ...filter, format: e.target.value })}
              >
                <option value="">{t("sidebar.allFormats")}</option>
                {formatIds.map((id) => (
                  <option key={id} value={id}>
                    {formatTitle(id)}
                  </option>
                ))}
              </select>
              <select
                aria-label={t("sidebar.filterChannel")}
                title={t("sidebar.filterChannel")}
                value={filter.channel ?? ""}
                onChange={(e) => change({ ...filter, channel: e.target.value })}
              >
                <option value="">{t("sidebar.allChannels")}</option>
                {channelIds.map((id) => (
                  <option key={id} value={id}>
                    {id}
                  </option>
                ))}
              </select>
            </div>
            <ErrorLine error={data.error} />
            {videos === null ? (
              !data.error && <p className="muted side-note">{t("common.loading")}</p>
            ) : videos.length === 0 ? (
              <p className="muted side-note">
                {filtering ? (
                  t("sidebar.noMatch")
                ) : (
                  <>
                    {t("sidebar.noVideos")} <a href={NEW_VIDEO_HASH}>{t("nav.newVideo")}</a>
                  </>
                )}
              </p>
            ) : (
              <ul>
                {videos.map((v) => (
                  <VideoItem key={v.slug} video={v} active={v.slug === current} />
                ))}
              </ul>
            )}
          </section>
        </div>
        <div className="shell-bottom">
          <div className="group">
            <ul>
              <li>
                <NavLink href={AGENT_HASH} hash={hash} active={isAgent(hash)} label={t("nav.agent")} />
              </li>
            </ul>
          </div>
          <LangSwitch />
        </div>
      </nav>
    </aside>
  );
}
