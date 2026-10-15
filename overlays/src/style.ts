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
  | "top-right"
  | "top-left"
  | "top-center"
  | "bottom-left"
  | "bottom-center";

export type OverlayPosition = { anchor: Anchor; x?: number; y: number };

/** Explicit placement: anchor type plus reference-px x/y ("top-right": x = right edge). */
export type AnchorSpec = { anchor: Anchor; x?: number; y: number; align?: "left" | "center" | "right" };

export type Style = {
  /** Output pixels. `reference_width` (default 1080) is the width every other pixel
   * number in style.json, presets.ts and slots.json is written for; see designScale. */
  canvas: {
    width: number;
    height: number;
    fps: number;
    reference_width?: number;
    /** style.json canvases name the canvas was resolved from (render.mjs sets it). */
    preset?: string;
  };
  /** Named placements for this canvas (style.json canvases.<name>.slots, reference
   * px); absent = src/slots.json. render.mjs swaps them in. */
  slots?: Record<string, unknown>;
  /** "overlay_positions": every overlay preset takes its anchor/x/y from
   * overlay_positions instead of its own (portrait) placement. Set by render.mjs
   * for a canvas preset with its own overlay_positions (landscape). */
  role_placement?: "preset" | "overlay_positions";
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
  /** Named placement from slots.json, or an explicit placement in reference px
   * (e.g. from a frame-aware picker); overrides the role's own anchor/x/y/align. */
  anchor?: string | AnchorSpec;
  /** Reference-px point a role with `arrow` points at (e.g. the person). */
  arrowTo?: [number, number];
  /** Overrides the role's scrim strength (0..1). */
  scrim?: number;
  /** Measurement only: "background" hides the glyphs (keeps scrim and boxes),
   * "glyphs" shows only the glyph fill. Default "all". */
  layers?: "all" | "background" | "glyphs";
  /** A font file in the render's public dir (render.mjs copies the Library font there):
   * replaces the family of every role; sizes, case and boxes stay. */
  fontFile?: string;
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

/** Width of the design space: presets, slots, safe_zone, overlay_positions, font
 * sizes and animation distances are all in pixels of a canvas this wide. */
export const REFERENCE_WIDTH = 1080;

/** The one scale factor of the overlay design: canvas pixels per reference pixel
 * (2 at 2160×3840). Overlay.tsx lays everything out in reference pixels and scales the
 * whole design by this factor, so a 4K overlay is the 1080 design at 2× size: font
 * sizes, paddings, radii, outlines, shadows, blur, ornaments, slots and the slide-in
 * distance all scale together, and rotation stays in degrees. */
export const designScale = (style: Style): number =>
  style.canvas.width / (style.canvas.reference_width ?? REFERENCE_WIDTH);

/** The canvas in reference pixels (1080×1920 for a 9:16 canvas with reference_width
 * 1080, 1920×1080 for 16:9 with reference_width 1920). */
export const referenceSize = (
  style: Style,
): { width: number; height: number } => {
  const k = designScale(style);
  return { width: style.canvas.width / k, height: style.canvas.height / k };
};

/** style.safe_zone in canvas pixels (style.json keeps it in reference pixels). */
export const scaledSafeZone = (style: Style): Style["safe_zone"] => {
  const k = designScale(style);
  const z = style.safe_zone;
  return {
    top: z.top * k,
    bottom: z.bottom * k,
    left: z.left * k,
    right: z.right * k,
    ...(z.right_rail
      ? {
          right_rail: {
            width: z.right_rail.width * k,
            from_y: z.right_rail.from_y * k,
          },
        }
      : {}),
  };
};

export type Box = { left: number; top: number; right: number; bottom: number };

/** Returns a list of violations (empty = inside the safe zone). `box` is in canvas
 * pixels; the safe zone is scaled from reference pixels by designScale. */
export const safeZoneViolations = (box: Box, style: Style): string[] => {
  const { width, height } = style.canvas;
  const z = scaledSafeZone(style);
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
