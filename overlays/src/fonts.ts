// Google fonts the presets (and style.json) can name, loaded through
// @remotion/google-fonts so no font files live in the repo. Only the face a render
// actually uses (family + style + weight) is fetched; loadFont() blocks rendering
// until it is ready.
import { loadFont as loadBodoniModa } from "@remotion/google-fonts/BodoniModa";
import { loadFont as loadCaveat } from "@remotion/google-fonts/Caveat";
import { loadFont as loadCormorantGaramond } from "@remotion/google-fonts/CormorantGaramond";
import { loadFont as loadCormorantSC } from "@remotion/google-fonts/CormorantSC";
import { loadFont as loadGreatVibes } from "@remotion/google-fonts/GreatVibes";
import { loadFont as loadInter } from "@remotion/google-fonts/Inter";
import { loadFont as loadInterTight } from "@remotion/google-fonts/InterTight";
import { loadFont as loadMontserrat } from "@remotion/google-fonts/Montserrat";
import { loadFont as loadPlayfair } from "@remotion/google-fonts/PlayfairDisplay";
import { loadFont as loadSpaceGrotesk } from "@remotion/google-fonts/SpaceGrotesk";
import { loadFont as loadSpecialElite } from "@remotion/google-fonts/SpecialElite";
import { loadFont as loadUnbounded } from "@remotion/google-fonts/Unbounded";

type AnyLoader = (
  style: "normal" | "italic",
  options: { weights: string[]; subsets: string[] },
) => { fontFamily: string; waitUntilDone: () => Promise<unknown> };

// Keyed by the lower-cased family name as written in style.json / presets.ts.
const LOADERS: Record<string, AnyLoader> = {
  "bodoni moda": loadBodoniModa as unknown as AnyLoader,
  caveat: loadCaveat as unknown as AnyLoader,
  "cormorant garamond": loadCormorantGaramond as unknown as AnyLoader,
  "cormorant sc": loadCormorantSC as unknown as AnyLoader,
  "great vibes": loadGreatVibes as unknown as AnyLoader,
  inter: loadInter as unknown as AnyLoader,
  "inter tight": loadInterTight as unknown as AnyLoader,
  montserrat: loadMontserrat as unknown as AnyLoader,
  "playfair display": loadPlayfair as unknown as AnyLoader,
  "space grotesk": loadSpaceGrotesk as unknown as AnyLoader,
  "special elite": loadSpecialElite as unknown as AnyLoader,
  unbounded: loadUnbounded as unknown as AnyLoader,
};

export type LoadedFont = {
  /** CSS font-family value. */
  css: string;
  /** False when the family is not in LOADERS (falls back to a local font). */
  known: boolean;
  /** Resolves when the face is loaded (needed before measuring text). */
  ready: Promise<unknown>;
};

const cache = new Map<string, LoadedFont>();

/** Load one face of a known Google font. Unknown families fall back to the plain
 * name (works only if installed locally) and are reported by the caller. */
export const loadFace = (family: string, weight: number, italic = false): LoadedFont => {
  const id = family.trim().toLowerCase();
  const key = `${id}|${weight}|${italic ? "i" : "n"}`;
  const hit = cache.get(key);
  if (hit) return hit;
  const loader = LOADERS[id];
  const out: LoadedFont = loader
    ? (() => {
        const f = loader(italic ? "italic" : "normal", {
          weights: [String(weight)],
          subsets: ["latin", "latin-ext"],
        });
        return { css: f.fontFamily, known: true, ready: f.waitUntilDone() };
      })()
    : { css: `"${family}", sans-serif`, known: false, ready: Promise.resolve() };
  cache.set(key, out);
  return out;
};

export const knownFamilies = (): string[] => Object.keys(LOADERS);
