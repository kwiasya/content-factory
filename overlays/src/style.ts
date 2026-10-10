// Types and pure helpers for the Style profile (repo-root style.json, schema cf-style/1).
// Only the fields the overlay renderer reads are typed; everything else passes through.
import { Easing } from "remotion";

export type OverlayType = "hook" | "place" | "fact" | "line";

export type FontSpec = {
  family: string;
  weight: number;
  size: number;
  case?: "sentence" | "upper" | "lower" | "as-is";
  file?: string | null;
};

/** "center": box centred horizontally, vertical centre at y. "middle-left": left
 * edge at x, vertical centre at y. "top-*": top edge at y.
 * "bottom-*": bottom edge at y (at rest, before the slide-in offset). "*-left": left
 * edge at x; "*-center": centred horizontally on the canvas. */
export type Anchor =
  | "center"
  | "middle-left"
  | "top-left"
  | "top-center"
  | "bottom-left"
  | "bottom-center";

export type OverlayPosition = { anchor: Anchor; x?: number; y: number };

export type Style = {
  canvas: { width: number; height: number; fps: number };
  safe_zone: {
    top: number;
    bottom: number;
    left: number;
    right: number;
    right_rail?: { width: number; from_y: number };
  };
  typography: {
    display: FontSpec;
    body: FontSpec;
    max_words_per_line: number;
    max_lines: number;
    /** Overlay preset from presets.ts; "legacy" (or absent) = the fields above. */
    preset?: string;
  };
  colors: {
    text: string;
    text_shadow?: string;
    accent?: string;
    backdrop: string;
  };
  overlay_positions: Record<OverlayType, OverlayPosition>;
  animation: {
    in: { type: string; frames: number; ease: string; distance_px: number };
    out: { type: string; frames: number; ease: string };
    min_hold_s?: number;
  };
};

export type OverlayProps = {
  text: string;
  type: OverlayType;
  durationInFrames: number;
  style: Style;
  /** Overrides style.typography.preset for this render. */
  preset?: string;
  /** Named placement from slots.json; overrides the role's own anchor/x/y/align. */
  anchor?: string;
  /** Overrides the role's scrim strength (0..1). */
  scrim?: number;
  /** Measurement only: "background" hides the glyphs (keeps scrim and boxes),
   * "glyphs" shows only the glyph fill. Default "all". */
  layers?: "all" | "background" | "glyphs";
};

export const fontRoleFor = (type: OverlayType): "display" | "body" =>
  type === "hook" || type === "place" ? "display" : "body";

export const applyCase = (text: string, c: FontSpec["case"]): string => {
  if (c === "upper") return text.toUpperCase();
  if (c === "lower") return text.toLowerCase();
  // "sentence" means: the author writes in sentence case; keep as written so
  // acronyms ("POV") and proper names survive.
  return text;
};

const CURVES: Record<string, (t: number) => number> = {
  linear: Easing.linear,
  quad: Easing.quad,
  cubic: Easing.cubic,
  sin: Easing.sin,
  exp: Easing.exp,
  circle: Easing.circle,
};

/** "out-cubic" | "in-cubic" | "in-out-quad" | "linear" -> easing function. */
export const easingFromName = (name: string): ((t: number) => number) => {
  const m = /^(in-out|in|out)-(\w+)$/.exec(name.trim());
  if (!m) return CURVES[name.trim()] ?? Easing.linear;
  const curve = CURVES[m[2]] ?? Easing.cubic;
  if (m[1] === "in") return Easing.in(curve);
  if (m[1] === "out") return Easing.out(curve);
  return Easing.inOut(curve);
};

export type Box = { left: number; top: number; right: number; bottom: number };

/** Returns a list of violations (empty = inside the safe zone). */
export const safeZoneViolations = (box: Box, style: Style): string[] => {
  const { width, height } = style.canvas;
  const z = style.safe_zone;
  const out: string[] = [];
  const minX = z.left;
  const maxX = width - z.right;
  const minY = z.top;
  const maxY = height - z.bottom;
  const r = (n: number) => Math.round(n);
  if (box.left < minX) out.push(`left ${r(box.left)} < ${minX}`);
  if (box.right > maxX) out.push(`right ${r(box.right)} > ${maxX}`);
  if (box.top < minY) out.push(`top ${r(box.top)} < ${minY}`);
  if (box.bottom > maxY) out.push(`bottom ${r(box.bottom)} > ${maxY}`);
  if (z.right_rail && box.bottom > z.right_rail.from_y) {
    const railX = width - z.right_rail.width;
    if (box.right > railX)
      out.push(
        `right ${r(box.right)} > ${railX} below y=${z.right_rail.from_y} (right rail)`,
      );
  }
  return out;
};
