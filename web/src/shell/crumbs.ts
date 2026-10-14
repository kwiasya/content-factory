import { CONTOUR_PREFIX, ideasHref, parseContour, watchlistHref } from "../contour/routes";
import type { FormatSummary } from "../formats/api";
import { FORMATS_PREFIX, formatHref, parseFormats } from "../formats/FormatsRoute";
import type { T } from "../i18n";
import { NOTES_HASH } from "../notes/NotesPage";
import { RESEARCH_PREFIX, parseResearch } from "../research/ResearchPage";
import { VIDEOS_PREFIX, parseVideos } from "../videos/routes";
import type { VideoSummary } from "../videos/videosApi";
import { SEARCH_PREFIX } from "../search/SearchPage";
import { AGENT_HASH, NEW_VIDEO_HASH, parseDoc, parseLibrary } from "./routes";

export interface Crumb {
  label: string;
  href?: string;
}

export interface CrumbContext {
  videos: VideoSummary[] | null;
  formats: FormatSummary[];
  t: T;
}

function formatTitle(formats: FormatSummary[], id: string): string {
  return formats.find((f) => f.id === id)?.title ?? id;
}

export function crumbs(hash: string, { videos, formats, t }: CrumbContext): Crumb[] {
  const research = { label: t("crumb.research"), href: CONTOUR_PREFIX };
  const agent = { label: t("crumb.agent"), href: AGENT_HASH };
  const videoRoute = parseVideos(hash);
  if (videoRoute?.slug) {
    const video = videos?.find((v) => v.slug === videoRoute.slug);
    if (!video) {
      return [{ label: t("crumb.videos"), href: VIDEOS_PREFIX }, { label: videoRoute.slug }];
    }
    const head = video.format
      ? { label: formatTitle(formats, video.format), href: formatHref(video.format) }
      : { label: t("crumb.videos"), href: VIDEOS_PREFIX };
    return [head, { label: video.title }];
  }
  const contour = parseContour(hash);
  if (contour) {
    switch (contour.page) {
      case "watchlist":
        return [research, { label: contour.name }];
      case "summary":
        return [research, { label: contour.name, href: watchlistHref(contour.name) }, { label: t("crumb.summaries") }];
      case "card":
        return [research, { label: t("crumb.reference", { id: contour.id }) }];
      case "ideas":
        return contour.id === null
          ? [research, { label: t("crumb.ideas") }]
          : [research, { label: t("crumb.ideas"), href: ideasHref() }, { label: `#${contour.id}` }];
      case "taxonomy":
        return [research, { label: t("crumb.taxonomy") }];
      default:
        return [{ label: t("crumb.research") }];
    }
  }
  const format = parseFormats(hash);
  if (format) {
    return format.id
      ? [{ label: t("crumb.formats"), href: FORMATS_PREFIX }, { label: formatTitle(formats, format.id) }]
      : [{ label: t("crumb.formats") }];
  }
  const doc = parseDoc(hash);
  if (doc !== null) {
    return [agent, { label: doc }];
  }
  const docs = parseResearch(hash);
  if (docs) {
    return docs.topic
      ? [agent, { label: t("crumb.researchDocs"), href: RESEARCH_PREFIX }, { label: docs.topic }]
      : [agent, { label: t("crumb.researchDocs") }];
  }
  if (hash.startsWith(SEARCH_PREFIX)) {
    return [{ label: t("crumb.search") }, { label: `“${decodeURIComponent(hash.slice(SEARCH_PREFIX.length))}”` }];
  }
  if (hash === NEW_VIDEO_HASH) return [{ label: t("crumb.newVideo") }];
  if (parseLibrary(hash)) return [{ label: t("crumb.library") }];
  if (hash === NOTES_HASH) return [{ label: t("crumb.notes") }];
  if (hash === AGENT_HASH) return [{ label: t("crumb.agent") }];
  return [{ label: t("crumb.videos") }];
}
