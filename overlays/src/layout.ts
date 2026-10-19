// Line breaking that respects both the word limits in style.json and the width
// the safe zone leaves. Runs in the browser after fonts are loaded.

let ctx: CanvasRenderingContext2D | null = null;
/** Width in px; `spacing` is CSS letter-spacing in px (also added after the last
 * glyph, as the browser does). */
const measure = (text: string, font: string, spacing = 0): number => {
  if (!ctx) ctx = document.createElement("canvas").getContext("2d");
  if (!ctx) return 0;
  ctx.font = font;
  ctx.letterSpacing = `${spacing}px`;
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
  /** "italic" or "normal" (default). */
  fontStyle?: string;
  /** Letter-spacing in em (0 = none). */
  letterSpacingEm?: number;
  maxWordsPerLine: number;
  maxLines: number;
  /** Prefer line breaks right after punctuation (",", ":", "."…) and lines of
   * even width, among the splits that fit. Off by default (legacy behaviour). */
  punctuationBreaks?: boolean;
  maxWidth: number;
  minScale?: number;
}): TextLayout => {
  // A "\n" in the text is a forced line break: each paragraph is laid out on its own
  // lines (word and line limits apply per paragraph), all at one font size.
  const paragraphs = opts.text.split(/\r?\n/).map((p) => p.trim()).filter(Boolean);
  if (paragraphs.length > 1) {
    const parts = paragraphs.map((p) => layoutText({ ...opts, text: p }));
    const fontSize = Math.min(...parts.map((l) => l.fontSize));
    const css = `${opts.fontStyle === "italic" ? "italic " : ""}${opts.fontWeight} ${fontSize}px ${opts.fontFamily}`;
    const lines = parts.flatMap((l) => l.lines);
    return {
      lines,
      fontSize,
      width: Math.max(...lines.map((l) => measure(l, css, (opts.letterSpacingEm ?? 0) * fontSize))),
      wordOverflow: parts.some((l) => l.wordOverflow),
      shrunk: parts.some((l) => l.shrunk),
    };
  }
  const words = opts.text.trim().split(/\s+/).filter(Boolean);
  const css = (size: number) =>
    `${opts.fontStyle === "italic" ? "italic " : ""}${opts.fontWeight} ${size}px ${opts.fontFamily}`;
  const em = opts.letterSpacingEm ?? 0;
  if (words.length === 0)
    return { lines: [], fontSize: opts.fontSize, width: 0, wordOverflow: false, shrunk: false };

  const font = css(opts.fontSize);
  const minLines = Math.ceil(words.length / opts.maxWordsPerLine);
  const wordOverflow = minLines > opts.maxLines;
  let best: { lines: string[]; width: number } | null = null;

  for (let k = Math.min(minLines, opts.maxLines); k <= Math.min(opts.maxLines, words.length); k++) {
    let bestK: { lines: string[]; width: number; score?: number } | null = null;
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
      const widths = lines.map((l) => measure(l, font, em * opts.fontSize));
      const width = Math.max(...widths);
      if (opts.punctuationBreaks) {
        // Score: overflow is worst, then breaks not after punctuation, then raggedness.
        const softBreaks = lines.slice(0, -1).filter((l) => !/[,.:;!?…–—·]$/.test(l)).length;
        const score =
          Math.max(0, width - opts.maxWidth) * 10 +
          softBreaks * 0.5 * opts.fontSize +
          (width - Math.min(...widths)) * 0.25 +
          width * 0.05;
        if (!bestK || score < (bestK.score ?? Infinity)) bestK = { lines, width, score };
      } else if (!bestK || width < bestK.width - 0.5) bestK = { lines, width };
    }
    if (!bestK) continue;
    if (!best || bestK.width < best.width) best = { lines: bestK.lines, width: bestK.width };
    if (bestK.width <= opts.maxWidth)
      return { lines: bestK.lines, width: bestK.width, fontSize: opts.fontSize, wordOverflow, shrunk: false };
  }

  // Nothing fits at full size: shrink the narrowest arrangement to the width.
  const chosen = best ?? {
    lines: [words.join(" ")],
    width: measure(words.join(" "), font, em * opts.fontSize),
  };
  const scale = Math.max(opts.minScale ?? 0.6, opts.maxWidth / chosen.width);
  const fontSize = Math.floor(opts.fontSize * scale);
  return {
    lines: chosen.lines,
    fontSize,
    width: Math.max(...chosen.lines.map((l) => measure(l, css(fontSize), em * fontSize))),
    wordOverflow,
    shrunk: true,
  };
};

/** A run of text in one colour; `c` undefined = the role's fill. */
export type Run = { t: string; c?: string };

/** Inline key-word mark: "{words}" or "{words|colour}". */
export const MARK_RE = /\{([^{}|]*)(?:\|([^{}]*))?\}/g;

/** Key-word marks in an overlay text. `colour` is a name in `palette`
 * (style.colors.key_words) or a CSS colour such as #FF4FA3; a bare mark takes
 * `fallback`. A mark may span a "\n". Returns the text without the marks (what layout
 * measures) and, per whitespace-separated word in order, its coloured runs: layoutText
 * keeps words and their order, so line k's words are the next ones in `words`. */
export const parseMarks = (
  raw: string,
  palette: Record<string, string> = {},
  fallback?: string,
): { text: string; words: Run[][]; marked: boolean } => {
  const chars: { ch: string; c?: string }[] = [];
  let last = 0;
  let marked = false;
  for (const m of raw.matchAll(MARK_RE)) {
    for (const ch of raw.slice(last, m.index)) chars.push({ ch });
    const name = (m[2] ?? "").trim();
    const c = name ? (palette[name] ?? name) : fallback;
    for (const ch of m[1]) chars.push({ ch, c });
    marked = true;
    last = (m.index ?? 0) + m[0].length;
  }
  for (const ch of raw.slice(last)) chars.push({ ch });
  const words: Run[][] = [];
  let cur: Run[] = [];
  for (const { ch, c } of chars) {
    if (/\s/.test(ch)) {
      if (cur.length) words.push(cur);
      cur = [];
      continue;
    }
    const tail = cur[cur.length - 1];
    if (tail && tail.c === c) tail.t += ch;
    else cur.push({ t: ch, c });
  }
  if (cur.length) words.push(cur);
  return { text: chars.map((x) => x.ch).join(""), words, marked };
};

/** The coloured runs of each laid-out line (see parseMarks), `cased` per run. */
export const lineRuns = (lines: string[], words: Run[][], cased: (t: string) => string): Run[][] => {
  let i = 0;
  return lines.map((line) => {
    const n = line.split(" ").filter(Boolean).length;
    const out: Run[] = [];
    for (const w of words.slice(i, i + n)) {
      if (out.length) out.push({ t: " " });
      for (const r of w) out.push({ t: cased(r.t), c: r.c });
    }
    i += n;
    return out;
  });
};
