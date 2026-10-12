export const VIDEOS_PREFIX = "#/videos";

export const videoHref = (slug: string) => `${VIDEOS_PREFIX}/${encodeURIComponent(slug)}`;

export function videosRoute(hash: string): { slug: string | null } | null {
  if (hash === VIDEOS_PREFIX || hash === `${VIDEOS_PREFIX}/`) {
    return { slug: null };
  }
  if (hash.startsWith(`${VIDEOS_PREFIX}/`)) {
    return { slug: decodeURIComponent(hash.slice(VIDEOS_PREFIX.length + 1)) };
  }
  return null;
}
