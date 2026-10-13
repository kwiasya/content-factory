export const DOC_PREFIX = "#/doc/";
export const AGENT_HASH = "#/agent";
export const LIBRARY_HASH = "#/library";
export const NEW_VIDEO_HASH = "#/new-video";

export const docHref = (path: string) => DOC_PREFIX + encodeURIComponent(path);

export function parseDoc(hash: string): string | null {
  return hash.startsWith(DOC_PREFIX) ? decodeURIComponent(hash.slice(DOC_PREFIX.length)) : null;
}
