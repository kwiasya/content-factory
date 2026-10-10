// Line breaking that respects both the word limits in style.json and the width
// the safe zone leaves. Runs in the browser after fonts are loaded.

let ctx: CanvasRenderingContext2D | null = null;
const measure = (text: string, font: string): number => {
  if (!ctx) ctx = document.createElement("canvas").getContext("2d");
  if (!ctx) return 0;
  ctx.font = font;
  return ctx.measureText(text).width;
};

/** All ways to cut `n` words into `k` contiguous non-empty groups. */
const partitions = (n: number, k: number): number[][] => {
  if (k === 1) return [[n]];
  const out: number[][] = [];
  for (let first = 1; first <= n - k + 1; first++)
    for (const rest of partitions(n - first, k - 1)) out.push([first, ...rest]);
  return out;
};

export type TextLayout = {
  lines: string[];
  fontSize: number;
  /** Widest line in px at fontSize. */
  width: number;
  /** Text needed more than max_lines lines at max_words_per_line. */
  wordOverflow: boolean;
  /** Font had to be shrunk to fit the width. */
  shrunk: boolean;
};

export const layoutText = (opts: {
  text: string;
  fontFamily: string;
  fontWeight: number;
  fontSize: number;
  maxWordsPerLine: number;
  maxLines: number;
  maxWidth: number;
  minScale?: number;
}): TextLayout => {
  const words = opts.text.trim().split(/\s+/).filter(Boolean);
  const css = (size: number) => `${opts.fontWeight} ${size}px ${opts.fontFamily}`;
  if (words.length === 0)
    return { lines: [], fontSize: opts.fontSize, width: 0, wordOverflow: false, shrunk: false };

  const font = css(opts.fontSize);
  const minLines = Math.ceil(words.length / opts.maxWordsPerLine);
  const wordOverflow = minLines > opts.maxLines;
  let best: { lines: string[]; width: number } | null = null;

  for (let k = Math.min(minLines, opts.maxLines); k <= Math.min(opts.maxLines, words.length); k++) {
    let bestK: { lines: string[]; width: number } | null = null;
    for (const sizes of partitions(words.length, k)) {
      // Respect the word limit, except when the text cannot fit it at all
      // (then only the last-line fold-in is allowed).
      if (!wordOverflow && sizes.some((s) => s > opts.maxWordsPerLine)) continue;
      if (wordOverflow && sizes.slice(0, -1).some((s) => s > opts.maxWordsPerLine)) continue;
      const lines: string[] = [];
      let i = 0;
      for (const s of sizes) {
        lines.push(words.slice(i, i + s).join(" "));
        i += s;
      }
      const width = Math.max(...lines.map((l) => measure(l, font)));
      if (!bestK || width < bestK.width - 0.5) bestK = { lines, width };
    }
    if (!bestK) continue;
    if (!best || bestK.width < best.width) best = bestK;
    if (bestK.width <= opts.maxWidth)
      return { ...bestK, fontSize: opts.fontSize, wordOverflow, shrunk: false };
  }

  // Nothing fits at full size: shrink the narrowest arrangement to the width.
  const chosen = best ?? { lines: [words.join(" ")], width: measure(words.join(" "), font) };
  const scale = Math.max(opts.minScale ?? 0.6, opts.maxWidth / chosen.width);
  const fontSize = Math.floor(opts.fontSize * scale);
  return {
    lines: chosen.lines,
    fontSize,
    width: Math.max(...chosen.lines.map((l) => measure(l, css(fontSize)))),
    wordOverflow,
    shrunk: true,
  };
};
