export const CONTOUR_PREFIX = "#/contour";

export type ContourView =
  | { page: "home" }
  | { page: "watchlist"; name: string }
  | { page: "summary"; name: string }
  | { page: "card"; id: string }
  | { page: "ideas"; id: number | null }
  | { page: "taxonomy" };

const enc = encodeURIComponent;

export const watchlistHref = (name: string) => `${CONTOUR_PREFIX}/watchlists/${enc(name)}`;
export const summaryHref = (name: string) => `${watchlistHref(name)}/summary`;
export const cardHref = (id: string) => `${CONTOUR_PREFIX}/cards/${enc(id)}`;
export const ideasHref = (id?: number) => `${CONTOUR_PREFIX}/ideas${id === undefined ? "" : `/${id}`}`;
export const taxonomyHref = () => `${CONTOUR_PREFIX}/taxonomy`;

export function parseContour(hash: string): ContourView | null {
  if (hash !== CONTOUR_PREFIX && !hash.startsWith(`${CONTOUR_PREFIX}/`)) {
    return null;
  }
  const parts = hash
    .slice(CONTOUR_PREFIX.length + 1)
    .split("/")
    .filter((p) => p !== "")
    .map((p) => decodeURIComponent(p));
  const [head, arg, tail] = parts;
  if (head === "watchlists" && arg) {
    return tail === "summary" ? { page: "summary", name: arg } : { page: "watchlist", name: arg };
  }
  if (head === "cards" && arg) {
    return { page: "card", id: arg };
  }
  if (head === "ideas") {
    const id = Number(arg);
    return { page: "ideas", id: arg && Number.isInteger(id) ? id : null };
  }
  if (head === "taxonomy") {
    return { page: "taxonomy" };
  }
  return { page: "home" };
}
