export const DOC_PREFIX = "#/doc/";
export const AGENT_HASH = "#/agent";
export const LIBRARY_HASH = "#/library";
export const NEW_VIDEO_HASH = "#/new-video";

export const docHref = (path: string) => DOC_PREFIX + encodeURIComponent(path);

export function parseDoc(hash: string): string | null {
  return hash.startsWith(DOC_PREFIX) ? decodeURIComponent(hash.slice(DOC_PREFIX.length)) : null;
}

export interface LibraryRoute {
  id: string | null;
  ref: string | null;
  query: URLSearchParams;
}

export function parseLibrary(hash: string): LibraryRoute | null {
  if (hash !== LIBRARY_HASH && !hash.startsWith(LIBRARY_HASH + "/") && !hash.startsWith(LIBRARY_HASH + "?")) {
    return null;
  }
  const rest = hash.slice(LIBRARY_HASH.length);
  const cut = rest.indexOf("?");
  const path = cut < 0 ? rest : rest.slice(0, cut);
  const query = new URLSearchParams(cut < 0 ? "" : rest.slice(cut + 1));
  if (path.startsWith("/ref/")) {
    return { id: null, ref: decodeURIComponent(path.slice(5)), query };
  }
  const id = path.length > 1 ? decodeURIComponent(path.slice(1)) : null;
  return { id, ref: null, query };
}

export function libraryHref(id: string | null = null, query?: URLSearchParams): string {
  const qs = query?.toString();
  return LIBRARY_HASH + (id ? `/${encodeURIComponent(id)}` : "") + (qs ? `?${qs}` : "");
}

export const libraryRefHref = (ref: string) => `${LIBRARY_HASH}/ref/${encodeURIComponent(ref)}`;
