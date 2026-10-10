// Google fonts named in style.json, loaded through @remotion/google-fonts so no
// font files live in the repo. loadFont() blocks rendering until the font is ready.
import { loadFont as loadInter } from "@remotion/google-fonts/Inter";
import { loadFont as loadPlayfair } from "@remotion/google-fonts/PlayfairDisplay";

const SUBSETS = { subsets: ["latin", "latin-ext"] as ("latin" | "latin-ext")[] };

const inter = loadInter("normal", {
  weights: ["400", "500", "600", "700"],
  ...SUBSETS,
});
const playfair = loadPlayfair("normal", {
  weights: ["400", "500", "600", "700"],
  ...SUBSETS,
});

const LOADED: Record<string, string> = {
  inter: inter.fontFamily,
  "playfair display": playfair.fontFamily,
};

/** CSS font-family for a style.json family name. Unknown families fall back to the
 * plain name (works only if installed locally) and are reported. */
export const cssFontFamily = (family: string): { css: string; known: boolean } => {
  const hit = LOADED[family.trim().toLowerCase()];
  return hit
    ? { css: hit, known: true }
    : { css: `"${family}", sans-serif`, known: false };
};

/** Resolves when every bundled font face is loaded (needed before measuring text). */
export const fontsReady: Promise<unknown> = Promise.all([
  inter.waitUntilDone(),
  playfair.waitUntilDone(),
]);
