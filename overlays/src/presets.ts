// Overlay presets: one coherent type system per name (font, weight, case, tracking,
// shadow, backdrop, decoration and placement for every overlay type). style.json
// `typography.preset` picks one; a render spec may override it with `preset`.
// "legacy" is the original design and is built from style.json itself.
//
// Canvas 1080×1920. Safe zone (style.json): y 269..1248, x 65..1015, and nothing
// right of x 850 below y 1150 (right rail). "bottom-*" anchors put the box's bottom
// edge at y at rest; the slide-in starts `animation.in.distance_px` lower, so
// bottom anchors sit at y ≤ 1248 - 24 = 1224.
import slotsJson from "./slots.json";
import { Anchor, fontRoleFor, FontSpec, OverlayType, Style } from "./style";

export type Slot = { anchor: Anchor; x?: number; y: number; align: "left" | "center" };
export const SLOTS: Record<string, Slot> = Object.fromEntries(
  Object.entries(slotsJson).filter(([k]) => !k.startsWith("_")),
) as Record<string, Slot>;

export type Ornament = {
  kind: "sparkle" | "heart" | "bow";
  /** Height in px. */
  size: number;
  gap: number;
  /** CSS colour, or "accent" for colors.accent. */
  color: string;
  side: "before" | "after" | "both";
};

export type RoleStyle = {
  family: string;
  weight: number;
  italic?: boolean;
  size: number;
  case: NonNullable<FontSpec["case"]>;
  /** Letter-spacing in em. */
  tracking?: number;
  lineHeight?: number;
  /** Text colour; default style.colors.text. */
  color?: string;
  /** CSS gradient used as the text fill (overrides color; use `filter` for glow). */
  gradient?: string;
  /** CSS text-shadow, or null for none. */
  shadow: string | null;
  /** Dark outline drawn behind the fill (a stroked copy of the text under it), so
   * hairlines survive compression. width = visible outline in px. */
  stroke?: { width: number; color: string } | null;
  /** Feathered dark ellipse behind the text block, 0..1 (centre alpha 0.6 × scrim). */
  scrim?: number;
  /** CSS filter on the text, e.g. drop-shadow glows that also work with gradients. */
  filter?: string;
  /** Rounded box behind the whole text block, or null. */
  backdrop: { color: string; padX: number; padY: number; radius: number } | null;
  /** Box behind each line separately (CapCut "background", marker highlight). */
  lineBox?: { color: string; padX: number; padY: number; radius: number; gap?: number } | null;
  anchor: Anchor;
  x?: number;
  y: number;
  align: "left" | "center";
  /** Cap on the box width in px (the safe zone also limits it). */
  maxWidth?: number;
  maxLines?: number;
  maxWordsPerLine?: number;
  /** Prefer breaking after punctuation; see layout.ts. */
  punctuationBreaks?: boolean;
  /** Degrees; layout and the safe-zone check ignore it. */
  rotate?: number;
  /** Thin line (or hand-drawn squiggle) above or below the text. `width: "text"`
   * matches the text width. */
  rule?: {
    width: number | "text";
    thickness: number;
    gap: number;
    color: string;
    position?: "above" | "below";
    kind?: "line" | "squiggle";
  } | null;
  /** Vertical bar left of the text, full text height. */
  bar?: { width: number; gap: number; color: string } | null;
  /** Small glyph(s) beside the text block. */
  ornament?: Ornament | null;
};

export type Preset = {
  label: string;
  /** One line for humans: what the system is. */
  note: string;
  roles: Record<OverlayType, RoleStyle>;
};


/** Legibility shadow for every box-free text: a tight contact shadow plus a wide soft one. */
const LEGIBLE = "0 2px 3px rgba(0,0,0,0.7), 0 10px 40px rgba(0,0,0,0.55)";
// Dark outlines drawn under the fill, so hairlines survive Instagram compression.
const SERIF_STROKE = { width: 2.5, color: "rgba(20,12,6,0.72)" };
const THIN_STROKE = { width: 2, color: "rgba(10,8,6,0.65)" };
const SCRIPT_STROKE = { width: 3, color: "rgba(70,12,40,0.9)" };
const PLUM_STROKE = { width: 2, color: "rgba(70,12,40,0.8)" };
const Y2K_STROKE = { width: 3, color: "rgba(55,8,75,0.9)" };
const THIN_Y2K_STROKE = { width: 2, color: "rgba(55,8,75,0.85)" };

const LEFT_X = 90;
const BOTTOM_Y = 1218;
/** Cap on hook width for left placements (the anchor picker keeps it off the person). */
const HOOK_COL = 760;
/** Cap on place-label width. */
const PLACE_COL = 640;

const CREAM = "#F5EFE6";
const PINK = "#F7C8D6";
/** Lighter pink for script fill: #F7C8D6 is L* 84, too close to pale stone. */
const PINK_LIGHT = "#FCDDE7";
const Y2K_GRADIENT = "linear-gradient(180deg, #FFF4FB 0%, #FFC2E6 45%, #DCC8FF 100%)";
const Y2K_GLOW =
  "drop-shadow(0 1px 1px rgba(70,10,90,0.8)) drop-shadow(0 0 5px rgba(255,120,205,0.55)) drop-shadow(0 4px 12px rgba(40,0,60,0.4))";

const bottomLeft = { anchor: "bottom-left" as const, x: LEFT_X, y: BOTTOM_Y, align: "left" as const };
const topLeft = { anchor: "top-left" as const, x: LEFT_X, y: 300, align: "left" as const };
const NO_BOX = { backdrop: null };

export const PRESETS: Record<string, Preset> = {
  "editorial-serif": {
    label: "1 Editorial serif",
    note: "Cormorant Garamond SemiBold Italic hook, Cormorant SC tracked place label; thin dark outline, layered shadow, soft scrim.",
    roles: {
      hook: {
        family: "Cormorant Garamond", weight: 600, italic: true, size: 96, case: "sentence",
        lineHeight: 0.98, shadow: LEGIBLE, stroke: SERIF_STROKE, scrim: 0.8, ...NO_BOX,
        ...bottomLeft, maxWidth: HOOK_COL, maxLines: 3, punctuationBreaks: true,
      },
      place: {
        family: "Cormorant SC", weight: 600, size: 48, case: "sentence", tracking: 0.1,
        lineHeight: 1.1, shadow: LEGIBLE, stroke: THIN_STROKE, scrim: 0.7, ...NO_BOX,
        ...bottomLeft, maxWidth: PLACE_COL,
      },
      fact: {
        family: "Cormorant Garamond", weight: 600, italic: true, size: 52, case: "sentence",
        lineHeight: 1.05, shadow: LEGIBLE, stroke: THIN_STROKE, scrim: 0.7, ...NO_BOX, ...topLeft,
        maxWidth: 800, punctuationBreaks: true,
      },
      line: {
        family: "Cormorant Garamond", weight: 600, italic: true, size: 84, case: "sentence",
        lineHeight: 1.0, shadow: LEGIBLE, stroke: SERIF_STROKE, scrim: 0.8, ...NO_BOX,
        ...bottomLeft, maxWidth: HOOK_COL, maxLines: 3, punctuationBreaks: true,
      },
    },
  },

  "clean-grotesk": {
    label: "2 Clean grotesk",
    note: "Inter Tight SemiBold sentence-case hook; tracked uppercase place label under a 2-px rule; layered shadow, soft scrim.",
    roles: {
      hook: {
        family: "Inter Tight", weight: 600, size: 86, case: "sentence", tracking: -0.02,
        lineHeight: 1.04, shadow: LEGIBLE, scrim: 0.7, ...NO_BOX, ...bottomLeft,
        maxWidth: HOOK_COL, maxLines: 3, punctuationBreaks: true,
      },
      place: {
        family: "Inter Tight", weight: 700, size: 40, case: "upper", tracking: 0.16,
        lineHeight: 1.15, shadow: LEGIBLE, scrim: 0.7, ...NO_BOX, ...bottomLeft, maxWidth: PLACE_COL,
        rule: { width: 64, thickness: 2, gap: 18, color: "rgba(255,255,255,0.95)" },
      },
      fact: {
        family: "Inter Tight", weight: 500, size: 44, case: "sentence", lineHeight: 1.15,
        shadow: LEGIBLE, scrim: 0.6, ...NO_BOX, ...topLeft, maxWidth: 800, punctuationBreaks: true,
      },
      line: {
        family: "Inter Tight", weight: 600, size: 84, case: "sentence", tracking: -0.02,
        lineHeight: 1.04, shadow: LEGIBLE, scrim: 0.7, ...NO_BOX, ...bottomLeft,
        maxWidth: HOOK_COL, maxLines: 3, punctuationBreaks: true,
      },
    },
  },

  "lower-third-tag": {
    label: "6 Lower-third tag",
    note: "Space Grotesk SemiBold; place as a left tag with an accent bar (colors.accent); layered shadow, soft scrim.",
    roles: {
      hook: {
        family: "Space Grotesk", weight: 600, size: 86, case: "sentence", tracking: -0.02,
        lineHeight: 1.04, shadow: LEGIBLE, scrim: 0.7, ...NO_BOX, anchor: "center", y: 820,
        align: "center", maxWidth: 900, maxLines: 3, punctuationBreaks: true,
      },
      place: {
        family: "Space Grotesk", weight: 600, size: 48, case: "sentence", tracking: -0.01,
        lineHeight: 1.1, shadow: LEGIBLE, scrim: 0.7, ...NO_BOX, ...bottomLeft, maxWidth: PLACE_COL,
        bar: { width: 6, gap: 20, color: "accent" },
      },
      fact: {
        family: "Space Grotesk", weight: 500, size: 44, case: "sentence", lineHeight: 1.15,
        shadow: LEGIBLE, scrim: 0.6, ...NO_BOX, ...topLeft, maxWidth: 800, punctuationBreaks: true,
        bar: { width: 6, gap: 20, color: "accent" },
      },
      line: {
        family: "Space Grotesk", weight: 600, size: 84, case: "sentence", tracking: -0.02,
        lineHeight: 1.04, shadow: LEGIBLE, scrim: 0.7, ...NO_BOX, anchor: "center", y: 820,
        align: "center", maxWidth: 900, maxLines: 3, punctuationBreaks: true,
      },
    },
  },

  "tiktok-hype": {
    label: "7 TikTok hype",
    note: "Montserrat ExtraBold uppercase, black text in solid white per-line boxes (CapCut style), hook tilted -3°.",
    roles: {
      hook: {
        family: "Montserrat", weight: 800, size: 56, case: "upper", tracking: -0.01,
        lineHeight: 1.22, color: "#111111", shadow: null, ...NO_BOX,
        lineBox: { color: "#FFFFFF", padX: 20, padY: 4, radius: 12 },
        anchor: "center", y: 640, align: "center", maxWidth: 860, rotate: -3,
        punctuationBreaks: true,
      },
      place: {
        family: "Montserrat", weight: 800, size: 32, case: "upper", tracking: 0.02,
        lineHeight: 1.3, color: "#111111", shadow: null, ...NO_BOX,
        lineBox: { color: "#FFFFFF", padX: 14, padY: 4, radius: 8 },
        ...bottomLeft, maxWidth: 470,
      },
      fact: {
        family: "Montserrat", weight: 700, size: 34, case: "sentence", lineHeight: 1.3,
        color: "#111111", shadow: null, ...NO_BOX,
        lineBox: { color: "#FFFFFF", padX: 14, padY: 4, radius: 8 },
        ...topLeft, maxWidth: 760, punctuationBreaks: true,
      },
      line: {
        family: "Montserrat", weight: 800, size: 48, case: "upper", lineHeight: 1.22,
        color: "#111111", shadow: null, ...NO_BOX,
        lineBox: { color: "#FFFFFF", padX: 18, padY: 4, radius: 10 },
        anchor: "center", y: 640, align: "center", maxWidth: 860, rotate: -3,
        punctuationBreaks: true,
      },
    },
  },

  "pinterest-aesthetic": {
    label: "8 Pinterest aesthetic",
    note: "Bodoni Moda SemiBold lowercase in cream, light tracking, centred; hairline under the place label; dark outline, layered shadow, scrim.",
    roles: {
      hook: {
        family: "Bodoni Moda", weight: 600, size: 84, case: "lower", tracking: 0.03,
        lineHeight: 1.08, color: CREAM, shadow: LEGIBLE, stroke: SERIF_STROKE, scrim: 0.8, ...NO_BOX,
        anchor: "center", y: 820, align: "center", maxWidth: 900, maxLines: 3,
        punctuationBreaks: true,
      },
      place: {
        family: "Bodoni Moda", weight: 600, size: 42, case: "lower", tracking: 0.1,
        lineHeight: 1.2, color: CREAM, shadow: LEGIBLE, stroke: THIN_STROKE, scrim: 0.9, ...NO_BOX,
        anchor: "center", y: 820, align: "center", maxWidth: 760,
        rule: { width: "text", thickness: 2, gap: 14, color: "rgba(245,239,230,0.95)", position: "below" },
      },
      fact: {
        family: "Bodoni Moda", weight: 600, italic: true, size: 44, case: "lower", tracking: 0.04,
        lineHeight: 1.25, color: CREAM, shadow: LEGIBLE, stroke: THIN_STROKE, scrim: 0.7, ...NO_BOX,
        anchor: "top-center", y: 320, align: "center", maxWidth: 800, maxLines: 3,
      },
      line: {
        family: "Bodoni Moda", weight: 600, size: 84, case: "lower", tracking: 0.03,
        lineHeight: 1.08, color: CREAM, shadow: LEGIBLE, stroke: SERIF_STROKE, scrim: 0.8, ...NO_BOX,
        anchor: "center", y: 820, align: "center", maxWidth: 900, maxLines: 3,
        punctuationBreaks: true,
      },
    },
  },

  "coquette-girly": {
    label: "9 Coquette girly",
    note: "Great Vibes script in soft pink with a 3-px plum outline, gently tilted; bold italic serif place label with a pink bow; scrim.",
    roles: {
      hook: {
        family: "Great Vibes", weight: 400, size: 104, case: "lower", lineHeight: 1.0,
        color: PINK_LIGHT, shadow: LEGIBLE, stroke: SCRIPT_STROKE, scrim: 1, ...NO_BOX, ...bottomLeft,
        y: 1200, maxWidth: 700, maxLines: 3, rotate: -4, punctuationBreaks: true,
      },
      place: {
        family: "Cormorant Garamond", weight: 700, italic: true, size: 52, case: "sentence",
        lineHeight: 1.1, color: "#FFF4F7", shadow: LEGIBLE, stroke: PLUM_STROKE, scrim: 0.7,
        ...NO_BOX, ...bottomLeft, maxWidth: PLACE_COL, rotate: -2,
        ornament: { kind: "bow", size: 50, gap: 14, color: PINK, side: "after" },
      },
      fact: {
        family: "Cormorant Garamond", weight: 700, italic: true, size: 48, case: "sentence",
        lineHeight: 1.1, color: "#FFF4F7", shadow: LEGIBLE, stroke: PLUM_STROKE, scrim: 0.7,
        ...NO_BOX, ...topLeft, maxWidth: 800, punctuationBreaks: true,
      },
      line: {
        family: "Great Vibes", weight: 400, size: 96, case: "lower", lineHeight: 1.0,
        color: PINK_LIGHT, shadow: LEGIBLE, stroke: SCRIPT_STROKE, scrim: 1, ...NO_BOX, ...bottomLeft,
        maxWidth: 700, maxLines: 3, rotate: -4, punctuationBreaks: true,
      },
    },
  },

  "y2k-gloss": {
    label: "10 Y2K gloss",
    note: "Unbounded ExtraBold, pastel pink-to-lilac gradient with a dark violet outline and pink glow; sparkles flank the place label; scrim.",
    roles: {
      hook: {
        family: "Unbounded", weight: 800, size: 84, case: "upper", lineHeight: 1.08,
        gradient: Y2K_GRADIENT, filter: Y2K_GLOW, shadow: LEGIBLE, stroke: Y2K_STROKE, scrim: 1,
        ...NO_BOX, anchor: "center", y: 820, align: "center", maxWidth: 920, maxLines: 4,
        maxWordsPerLine: 2, punctuationBreaks: true,
      },
      place: {
        family: "Unbounded", weight: 800, size: 40, case: "upper", lineHeight: 1.12,
        gradient: Y2K_GRADIENT, filter: Y2K_GLOW, shadow: LEGIBLE, stroke: THIN_Y2K_STROKE,
        scrim: 0.8, ...NO_BOX, ...bottomLeft, maxWidth: 640,
        ornament: { kind: "sparkle", size: 40, gap: 14, color: "#FFE6F6", side: "both" },
      },
      fact: {
        family: "Unbounded", weight: 700, size: 40, case: "sentence", lineHeight: 1.15,
        gradient: Y2K_GRADIENT, filter: Y2K_GLOW, shadow: LEGIBLE, stroke: THIN_Y2K_STROKE,
        scrim: 0.8, ...NO_BOX, ...topLeft, maxWidth: 800, punctuationBreaks: true,
      },
      line: {
        family: "Unbounded", weight: 800, size: 84, case: "upper", lineHeight: 1.08,
        gradient: Y2K_GRADIENT, filter: Y2K_GLOW, shadow: LEGIBLE, stroke: Y2K_STROKE, scrim: 1,
        ...NO_BOX, anchor: "center", y: 820, align: "center", maxWidth: 920, maxLines: 4,
        maxWordsPerLine: 2, punctuationBreaks: true,
      },
    },
  },

  "diary-typewriter": {
    label: "11 Diary typewriter",
    note: "Special Elite lowercase, dark ink on a cream marker strip behind each line, top-left like a journal entry.",
    roles: {
      hook: {
        family: "Special Elite", weight: 400, size: 52, case: "lower", lineHeight: 1.42,
        color: "#2A2320", shadow: null, ...NO_BOX,
        lineBox: { color: "rgba(245,239,230,0.88)", padX: 12, padY: 2, radius: 2 },
        ...topLeft, maxWidth: 780, maxLines: 3, punctuationBreaks: true,
      },
      place: {
        family: "Special Elite", weight: 400, size: 40, case: "lower", lineHeight: 1.4,
        color: "#2A2320", shadow: null, ...NO_BOX,
        lineBox: { color: "rgba(245,239,230,0.88)", padX: 10, padY: 2, radius: 2 },
        ...topLeft, maxWidth: 600,
      },
      fact: {
        family: "Special Elite", weight: 400, size: 34, case: "lower", lineHeight: 1.4,
        color: "#2A2320", shadow: null, ...NO_BOX,
        lineBox: { color: "rgba(245,239,230,0.88)", padX: 10, padY: 2, radius: 2 },
        ...topLeft, y: 380, maxWidth: 780, maxLines: 3, punctuationBreaks: true,
      },
      line: {
        family: "Special Elite", weight: 400, size: 42, case: "lower", lineHeight: 1.42,
        color: "#2A2320", shadow: null, ...NO_BOX,
        lineBox: { color: "rgba(245,239,230,0.88)", padX: 12, padY: 2, radius: 2 },
        ...topLeft, maxWidth: 780, maxLines: 3, punctuationBreaks: true,
      },
    },
  },

  "handwritten-note": {
    label: "12 Handwritten note",
    note: "Caveat Bold in white with a dark outline and a hand-drawn squiggle underline; layered shadow, scrim.",
    roles: {
      hook: {
        family: "Caveat", weight: 700, size: 104, case: "sentence", lineHeight: 0.98,
        shadow: LEGIBLE, stroke: THIN_STROKE, scrim: 0.7, ...NO_BOX, ...bottomLeft, y: 1210,
        maxWidth: HOOK_COL, maxLines: 3, rotate: -2, punctuationBreaks: true,
        rule: { width: "text", thickness: 6, gap: 2, color: "#FFFFFF", position: "below", kind: "squiggle" },
      },
      place: {
        family: "Caveat", weight: 700, size: 72, case: "sentence", lineHeight: 1.0,
        shadow: LEGIBLE, stroke: THIN_STROKE, scrim: 0.7, ...NO_BOX, anchor: "bottom-left",
        x: LEFT_X, y: 1040, align: "left", maxWidth: PLACE_COL, rotate: -2,
        rule: { width: "text", thickness: 5, gap: 0, color: "#FFFFFF", position: "below", kind: "squiggle" },
      },
      fact: {
        family: "Caveat", weight: 700, size: 64, case: "sentence", lineHeight: 1.0,
        shadow: LEGIBLE, stroke: THIN_STROKE, scrim: 0.6, ...NO_BOX, ...topLeft, maxWidth: 800,
        rotate: -2, punctuationBreaks: true,
      },
      line: {
        family: "Caveat", weight: 700, size: 96, case: "sentence", lineHeight: 0.98,
        shadow: LEGIBLE, stroke: THIN_STROKE, scrim: 0.7, ...NO_BOX, ...bottomLeft,
        maxWidth: HOOK_COL, maxLines: 3, rotate: -2, punctuationBreaks: true,
      },
    },
  },
};

export const PRESET_NAMES = ["legacy", ...Object.keys(PRESETS)];

/** The original design: fonts, colours and positions straight from style.json,
 * translucent pill behind the text. */
const legacyRole = (style: Style, type: OverlayType): RoleStyle => {
  const font = style.typography[fontRoleFor(type)];
  const pos = style.overlay_positions[type];
  return {
    family: font.family,
    weight: font.weight,
    size: font.size,
    case: font.case ?? "sentence",
    lineHeight: 1.18,
    shadow: style.colors.text_shadow ? `0 2px 12px ${style.colors.text_shadow}` : null,
    backdrop: { color: style.colors.backdrop, padX: 28, padY: 16, radius: 24 },
    anchor: pos.anchor,
    x: pos.x,
    y: pos.y,
    align: pos.anchor === "center" || pos.anchor.endsWith("-center") ? "center" : "left",
  };
};

/** Role style for one overlay. Throws on an unknown preset name. */
export const resolveRole = (
  style: Style,
  type: OverlayType,
  presetName: string | undefined,
  override: { anchor?: string; scrim?: number } = {},
): RoleStyle => {
  const base = baseRole(style, type, presetName);
  let out = base;
  if (override.anchor) {
    const slot = SLOTS[override.anchor];
    if (!slot)
      throw new Error(
        `[cf-overlay] unknown anchor "${override.anchor}"; known: ${Object.keys(SLOTS).join(", ")}`,
      );
    out = { ...out, anchor: slot.anchor, x: slot.x, y: slot.y, align: slot.align };
  }
  if (typeof override.scrim === "number") out = { ...out, scrim: override.scrim };
  return out;
};

const baseRole = (style: Style, type: OverlayType, presetName: string | undefined): RoleStyle => {
  const name = (presetName ?? "legacy").trim() || "legacy";
  if (name === "legacy") return legacyRole(style, type);
  const preset = PRESETS[name];
  if (!preset)
    throw new Error(
      `[cf-overlay] unknown preset "${name}"; known: ${PRESET_NAMES.join(", ")}`,
    );
  const role = preset.roles[type];
  const resolveColor = (c: string) => (c === "accent" ? (style.colors.accent ?? "#F2C14E") : c);
  return {
    ...role,
    color: role.color ?? style.colors.text,
    bar: role.bar ? { ...role.bar, color: resolveColor(role.bar.color) } : role.bar,
    ornament: role.ornament
      ? { ...role.ornament, color: resolveColor(role.ornament.color) }
      : role.ornament,
  };
};
