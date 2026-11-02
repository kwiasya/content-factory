export const VIDEOS_PREFIX = "#/videos";

export const videoHref = (slug: string, tab?: string) =>
  `${VIDEOS_PREFIX}/${encodeURIComponent(slug)}${tab ? `?tab=${encodeURIComponent(tab)}` : ""}`;

export function parseVideos(hash: string): { slug: string | null; tab: string | null } | null {
  if (hash === VIDEOS_PREFIX || hash === `${VIDEOS_PREFIX}/`) {
    return { slug: null, tab: null };
  }
  if (hash.startsWith(`${VIDEOS_PREFIX}/`)) {
    const [path, query = ""] = hash.slice(VIDEOS_PREFIX.length + 1).split("?", 2);
    return { slug: decodeURIComponent(path), tab: new URLSearchParams(query).get("tab") };
  }
  return null;
}
