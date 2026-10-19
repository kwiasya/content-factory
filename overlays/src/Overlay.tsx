import React, { useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import {
  AbsoluteFill,
  cancelRender,
  CalculateMetadataFunction,
  interpolate,
  useCurrentFrame,
  useDelayRender,
} from "remotion";
import { loadFace, loadFileFace } from "./fonts";
import { layoutText, lineRuns, parseMarks, TextLayout } from "./layout";
import { ListStyle, Ornament, resolveRole, RoleStyle } from "./presets";
import {
  applyCase,
  designScale,
  easingFromName,
  OverlayProps,
  referenceSize,
  safeZoneViolations,
  Style,
} from "./style";

/** Size, fps and length come from props, so one composition serves every overlay.
 * The size is the output canvas (style.canvas, 2160×3840 by default); the design inside
 * is laid out in reference pixels and scaled by designScale (see style.ts). */
export const calculateOverlayMetadata: CalculateMetadataFunction<
  OverlayProps
> = ({ props }) => ({
  width: props.style.canvas.width,
  height: props.style.canvas.height,
  fps: props.style.canvas.fps,
  durationInFrames: Math.max(1, Math.round(props.durationInFrames)),
  defaultCodec: "prores",
  defaultProResProfile: "4444",
  defaultPixelFormat: "yuva444p10le",
  defaultVideoImageFormat: "png",
});

const warn = (msg: string) => {
  // The marker lets render.mjs pick the line out of the browser log.
  console.warn(`[cf-overlay] WARN ${msg}`);
};

/** A round outline `w` px wide as hard text-shadows: copies of the glyphs on circles of radius
 * w and w/2 (a round dilation, like an outer stroke with round joins; -webkit-text-stroke
 * always draws mitred corners in Chrome). */
const roundOutline = (w: number, color: string): string => {
  const out: string[] = [];
  for (const [r, n] of [[w, 32], [w / 2, 16]] as const)
    for (let i = 0; i < n; i++) {
      const a = (2 * Math.PI * i) / n;
      out.push(`${(r * Math.cos(a)).toFixed(3)}px ${(r * Math.sin(a)).toFixed(3)}px 0 ${color}`);
    }
  return out.join(", ");
};

const isCenterAnchor = (a: RoleStyle["anchor"]) => a === "center" || a.endsWith("-center");

const ornamentWidth = (o: Ornament) => (o.kind === "bow" ? o.size * 1.5 : o.size);

/** Small inline SVG glyphs, so they do not depend on the font's symbol coverage. */
const OrnamentSvg: React.FC<{ o: Ornament; hidden?: boolean }> = ({ o, hidden }) => {
  const w = ornamentWidth(o);
  const glow = {
    filter: "drop-shadow(0 2px 3px rgba(0,0,0,0.6)) drop-shadow(0 6px 16px rgba(0,0,0,0.4))",
    flexShrink: 0,
    visibility: hidden ? "hidden" : "visible",
  } as const;
  if (o.kind === "sparkle")
    return (
      <svg width={w} height={o.size} viewBox="-1 -1 2 2" style={glow}>
        <path
          d="M0,-1 C0.08,-0.2 0.2,-0.08 1,0 C0.2,0.08 0.08,0.2 0,1 C-0.08,0.2 -0.2,0.08 -1,0 C-0.2,-0.08 -0.08,-0.2 0,-1Z"
          fill={o.color}
        />
      </svg>
    );
  if (o.kind === "heart")
    return (
      <svg width={w} height={o.size} viewBox="0 0 24 22" style={glow}>
        <path
          d="M12 21s-8.5-5.3-10.6-10.1C-0.3 6.6 2.4 1.5 6.8 1.5c2.4 0 4.1 1.4 5.2 3.2 1.1-1.8 2.8-3.2 5.2-3.2 4.4 0 7.1 5.1 5.4 9.4C20.5 15.7 12 21 12 21z"
          fill="none"
          stroke={o.color}
          strokeWidth={2}
        />
      </svg>
    );
  // Bow: two loops, a knot and two tails.
  return (
    <svg width={w} height={o.size} viewBox="0 0 36 24" style={glow}>
      <g fill={o.color} stroke="rgba(120,40,70,0.35)" strokeWidth={0.6}>
        <path d="M17 10 C11 2 2 1 2 7 C2 13 11 13 17 11 Z" />
        <path d="M19 10 C25 2 34 1 34 7 C34 13 25 13 19 11 Z" />
        <path d="M16.5 11.5 L11 23 L14.5 21.5 L17 23.5 L18 12 Z" />
        <path d="M19.5 11.5 L25 23 L21.5 21.5 L19 23.5 L18 12 Z" />
        <ellipse cx={18} cy={10.5} rx={2.6} ry={2.4} />
      </g>
    </svg>
  );
};

/** Hand-drawn-looking wavy line, `width` px wide. */
const Squiggle: React.FC<{ width: number; thickness: number; color: string }> = ({
  width,
  thickness,
  color,
}) => {
  const h = 16;
  const period = 34;
  const n = Math.max(2, Math.round(width / period));
  const step = width / n;
  let d = `M ${thickness} ${h / 2}`;
  for (let i = 0; i < n; i++) {
    const x0 = thickness + i * step;
    // Amplitude drifts a little so it does not look machine-made.
    const a = 4 + 1.5 * Math.sin(i * 1.7);
    d += ` Q ${x0 + step / 4} ${h / 2 - a} ${x0 + step / 2} ${h / 2} T ${x0 + step} ${h / 2}`;
  }
  return (
    <svg
      width={width + 2 * thickness}
      height={h}
      style={{ display: "block", overflow: "visible", filter: "drop-shadow(0 1px 4px rgba(0,0,0,0.4))" }}
    >
      <path d={d} fill="none" stroke={color} strokeWidth={thickness} strokeLinecap="round" />
    </svg>
  );
};

/** iOS-Notes-like checklist circle: filled with a white tick when done, a ring when open. */
const TickCircle: React.FC<{ size: number; done: boolean; on: string; off: string }> = ({ size, done, on, off }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" style={{ flexShrink: 0 }}>
    {done ? (
      <>
        <circle cx={12} cy={12} r={11} fill={on} />
        <path d="M7 12.5 L10.5 16 L17.5 8.5" fill="none" stroke="#FFFFFF" strokeWidth={2.4} strokeLinecap="round" strokeLinejoin="round" />
      </>
    ) : (
      <circle cx={12} cy={12} r={10.5} fill="none" stroke={off} strokeWidth={1.8} />
    )}
  </svg>
);

type ListEntry = { kind: "title" | "done" | "todo" | "recv" | "sent"; layout: TextLayout };

/** "[x] a" / "[ ] a" / "> a" / plain → entry kinds for the list modes. */
const parseEntry = (line: string, mode: ListStyle["mode"]): { kind: ListEntry["kind"]; text: string } => {
  const t = line.trim();
  if (mode === "checklist") {
    const m = /^\[( |x|X)\]\s*(.*)$/.exec(t);
    if (m) return { kind: m[1] === " " ? "todo" : "done", text: m[2] };
    return { kind: "title", text: t };
  }
  if (t.startsWith(">")) return { kind: "sent", text: t.slice(1).trim() };
  return { kind: "recv", text: t };
};

/** Hand-drawn arrow (quadratic curve + open head) from `from` to `to`, reference px. */
const Arrow: React.FC<{ from: [number, number]; to: [number, number]; color: string; thickness: number; W: number; H: number }> = ({
  from,
  to,
  color,
  thickness,
  W,
  H,
}) => {
  const [x1, y1] = from;
  const [x2, y2] = to;
  const dx = x2 - x1;
  const dy = y2 - y1;
  const len = Math.hypot(dx, dy) || 1;
  // Bend to one side by a quarter of the length, like a quick pen stroke.
  const nx = -dy / len;
  const ny = dx / len;
  const cx = (x1 + x2) / 2 + nx * len * 0.22;
  const cy = (y1 + y2) / 2 + ny * len * 0.22;
  const tx = x2 - cx;
  const ty = y2 - cy;
  const tl = Math.hypot(tx, ty) || 1;
  const head = Math.max(26, thickness * 5);
  const wing = (a: number) => {
    const c = Math.cos(a);
    const s2 = Math.sin(a);
    const ux = -(tx / tl);
    const uy = -(ty / tl);
    return [x2 + head * (ux * c - uy * s2), y2 + head * (ux * s2 + uy * c)];
  };
  const [ax, ay] = wing(0.5);
  const [bx, by] = wing(-0.45);
  return (
    <svg
      width={W}
      height={H}
      style={{ position: "absolute", left: 0, top: 0, overflow: "visible", filter: "drop-shadow(0 2px 3px rgba(0,0,0,0.6)) drop-shadow(0 6px 18px rgba(0,0,0,0.35))" }}
    >
      <g fill="none" stroke={color} strokeWidth={thickness} strokeLinecap="round" strokeLinejoin="round">
        <path d={`M ${x1} ${y1} Q ${cx} ${cy} ${x2} ${y2}`} />
        <path d={`M ${ax} ${ay} L ${x2} ${y2} L ${bx} ${by}`} />
      </g>
    </svg>
  );
};

/** Width available to the text, in reference pixels: safe zone (incl. the right rail
 * when the box can reach below it), the role's own cap, minus backdrop padding and the
 * accent bar. */
const textMaxWidth = (role: RoleStyle, style: Style): number => {
  const W = referenceSize(style).width;
  const z = style.safe_zone;
  const lines = role.maxLines ?? style.typography.max_lines;
  const estH = lines * role.size * (role.lineHeight ?? 1.18) + 2 * (role.backdrop?.padY ?? 0);
  const estBottom = role.anchor.startsWith("bottom")
    ? role.y
    : role.anchor === "center" || role.anchor === "middle-left"
      ? role.y + estH / 2
      : role.y + estH;
  const rail = z.right_rail && estBottom > z.right_rail.from_y ? z.right_rail : null;
  let avail: number;
  if (isCenterAnchor(role.anchor)) {
    let half = W / 2 - z.left;
    if (rail) half = Math.min(half, W - rail.width - W / 2);
    avail = 2 * half;
  } else if (role.anchor === "top-right") {
    avail = Math.min(role.x ?? W - z.right, rail ? W - rail.width : W - z.right) - z.left;
  } else {
    const right = rail ? W - rail.width : W - z.right;
    avail = right - (role.x ?? z.left);
  }
  if (role.maxWidth) avail = Math.min(avail, role.maxWidth);
  const o = role.ornament;
  const l = role.list;
  const listExtra = l
    ? l.mode === "checklist"
      ? role.size * 1.1 + 14
      : 2 * (l.bubblePadX ?? 0)
    : 0;
  const extra =
    listExtra +
    2 * (role.backdrop?.padX ?? 0) +
    2 * (role.lineBox?.padX ?? 0) +
    (role.bar ? role.bar.width + role.bar.gap : 0) +
    (o ? (o.side === "both" ? 2 : 1) * (ornamentWidth(o) + o.gap) : 0);
  return avail - extra;
};

/** Checklist rows or chat bubbles, one per entry (see RoleStyle.list). */
const ListBlock: React.FC<{
  entries: ListEntry[];
  list: ListStyle;
  role: RoleStyle;
  faceCss: string;
  titleCss: string;
  titleWeight: number;
  defaultColor: string;
  showGlyphs: boolean;
  showBackground: boolean;
}> = ({ entries, list, role, faceCss, titleCss, titleWeight, defaultColor, showGlyphs, showBackground }) => {
  const lh = role.lineHeight ?? 1.18;
  const glyphVis = showGlyphs ? "visible" : "hidden";
  if (list.mode === "checklist") {
    const icon = Math.round(role.size * 1.1);
    return (
      <div style={{ display: "flex", flexDirection: "column", rowGap: list.gap, color: defaultColor }}>
        {entries.map((e, i) =>
          e.kind === "title" ? (
            <div
              key={i}
              style={{ fontFamily: titleCss, fontWeight: titleWeight, fontSize: e.layout.fontSize, lineHeight: lh, visibility: glyphVis }}
            >
              {e.layout.lines.map((ln, k) => (
                <div key={k} style={{ whiteSpace: "nowrap" }}>{ln}</div>
              ))}
            </div>
          ) : (
            <div key={i} style={{ display: "flex", alignItems: "flex-start", columnGap: 14 }}>
              <div style={{ height: e.layout.fontSize * lh, display: "flex", alignItems: "center", visibility: showBackground ? "visible" : "hidden" }}>
                <TickCircle size={icon} done={e.kind === "done"} on={list.tickOn ?? "#F2B300"} off={list.tickOff ?? "#C7C7CC"} />
              </div>
              <div style={{ fontFamily: faceCss, fontWeight: role.weight, fontSize: e.layout.fontSize, lineHeight: lh, visibility: glyphVis }}>
                {e.layout.lines.map((ln, k) => (
                  <div key={k} style={{ whiteSpace: "nowrap" }}>{ln}</div>
                ))}
              </div>
            </div>
          ),
        )}
      </div>
    );
  }
  // Bubbles: received on the left in grey, sent on the right in blue; the last bubble
  // of a run gets the tail.
  const r = list.bubbleRadius ?? 32;
  return (
    <div style={{ display: "flex", flexDirection: "column", rowGap: list.gap, alignItems: "stretch" }}>
      {entries.map((e, i) => {
        const sent = e.kind === "sent";
        const c = sent ? (list.sent ?? { bg: "#0A84FF", color: "#FFFFFF" }) : (list.recv ?? { bg: "#E9E9EB", color: "#000000" });
        const lastOfRun = i === entries.length - 1 || (entries[i + 1].kind === "sent") !== sent;
        return (
          <div key={i} style={{ display: "flex", justifyContent: sent ? "flex-end" : "flex-start" }}>
            <div
              style={{
                position: "relative",
                backgroundColor: showBackground ? c.bg : undefined,
                color: c.color,
                borderRadius: r,
                borderBottomRightRadius: sent && lastOfRun ? r * 0.35 : r,
                borderBottomLeftRadius: !sent && lastOfRun ? r * 0.35 : r,
                padding: `${list.bubblePadY ?? 12}px ${list.bubblePadX ?? 22}px`,
                fontFamily: faceCss,
                fontWeight: role.weight,
                fontSize: e.layout.fontSize,
                lineHeight: lh,
                boxShadow: showBackground ? "0 4px 18px rgba(0,0,0,0.18)" : undefined,
              }}
            >
              <div style={{ visibility: glyphVis }}>
                {e.layout.lines.map((ln, k) => (
                  <div key={k} style={{ whiteSpace: "nowrap" }}>{ln}</div>
                ))}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
};

export const Overlay: React.FC<OverlayProps> = ({
  text: rawText,
  type,
  durationInFrames,
  style,
  preset,
  anchor: anchorOverride,
  scrim: scrimOverride,
  size: sizeOverride,
  layers = "all",
  arrowTo,
  fontFile,
}) => {
  const frame = useCurrentFrame();
  // Key-word marks "{words}" / "{words|colour}": layout measures the plain text, the fill
  // draws the marked words in their colour; the outline stays the role's.
  const marks = useMemo(
    () => parseMarks(rawText, style.colors.key_words, style.colors.accent),
    [rawText, style.colors.key_words, style.colors.accent],
  );
  const text = marks.text;
  const boxRef = useRef<HTMLDivElement>(null);
  const anchorRef = useRef<HTMLDivElement>(null);

  const presetName = preset ?? style.typography.preset ?? "legacy";
  const role = useMemo(
    () => resolveRole(style, type, presetName, { anchor: anchorOverride, scrim: scrimOverride, size: sizeOverride }),
    [style, type, presetName, anchorOverride, scrimOverride, sizeOverride],
  );
  const showGlyphs = layers !== "background";
  const showDecor = layers === "all";
  const showBackground = layers !== "glyphs";
  const face = useMemo(
    () => (fontFile ? loadFileFace(fontFile) : loadFace(role.family, role.weight, role.italic)),
    [fontFile, role.family, role.weight, role.italic],
  );
  const titleWeight = role.list?.titleWeight ?? role.weight;
  const titleFace = useMemo(
    () => (fontFile ? face : loadFace(role.family, titleWeight, role.italic)),
    [fontFile, face, role.family, titleWeight, role.italic],
  );

  // Hold the frame until the font is in, so line breaks are measured with it.
  const { delayRender, continueRender } = useDelayRender();
  const [fontsLoaded, setFontsLoaded] = useState(false);
  const [handle] = useState(() => delayRender("cf-overlay fonts"));
  useEffect(() => {
    Promise.all([face.ready, titleFace.ready]).then(
      () => {
        setFontsLoaded(true);
        continueRender(handle);
      },
      (err) => cancelRender(new Error(`cf-overlay font did not load${fontFile ? ` (${fontFile})` : ""}: ${err}`)),
    );
  }, [continueRender, handle, face, titleFace, fontFile]);

  const maxWidth = textMaxWidth(role, style);
  const tracking = role.tracking ?? 0;
  // A role with a title block: the lines before the first blank line are the title.
  const parts = useMemo(() => {
    const m = role.title && !role.list ? /\r?\n[ \t]*\r?\n/.exec(text) : null;
    return m ? { title: text.slice(0, m.index), body: text.slice(m.index + m[0].length) } : { title: null, body: text };
  }, [role.title, role.list, text]);
  const layoutPart = (t: string, size: number): TextLayout =>
    layoutText({
      text: applyCase(t, role.case),
      fontFamily: face.css,
      fontWeight: role.weight,
      fontStyle: role.italic ? "italic" : "normal",
      fontSize: size,
      letterSpacingEm: tracking,
      maxWordsPerLine: role.maxWordsPerLine ?? style.typography.max_words_per_line,
      maxLines: role.maxLines ?? style.typography.max_lines,
      maxWidth,
      punctuationBreaks: role.punctuationBreaks,
    });
  const layout: TextLayout | null = useMemo(
    () => (fontsLoaded ? layoutPart(parts.body, role.size) : null),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [fontsLoaded, parts.body, role, face.css, tracking, style.typography, maxWidth],
  );
  const titleLayout: TextLayout | null = useMemo(
    () => (fontsLoaded && parts.title !== null && role.title ? layoutPart(parts.title, role.title.size) : null),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [fontsLoaded, parts.title, role, face.css, tracking, style.typography, maxWidth],
  );

  // List modes: every "\n" line is its own entry, laid out on its own.
  const entries: ListEntry[] | null = useMemo(() => {
    const l = role.list;
    if (!fontsLoaded || !l) return null;
    return text
      .split(/\r?\n/)
      .filter((x) => x.trim())
      .map((raw) => {
        const { kind, text: t } = parseEntry(raw, l.mode);
        const isTitle = kind === "title";
        const size = isTitle ? role.size * (l.titleScale ?? 1) : role.size;
        return {
          kind,
          layout: layoutText({
            text: applyCase(t, role.case),
            fontFamily: isTitle ? titleFace.css : face.css,
            fontWeight: isTitle ? titleWeight : role.weight,
            fontStyle: role.italic ? "italic" : "normal",
            fontSize: size,
            letterSpacingEm: tracking,
            maxWordsPerLine: role.maxWordsPerLine ?? style.typography.max_words_per_line,
            maxLines: role.maxLines ?? style.typography.max_lines,
            maxWidth,
            punctuationBreaks: role.punctuationBreaks,
          }),
        };
      });
  }, [fontsLoaded, role, text, face.css, titleFace.css, titleWeight, tracking, style.typography, maxWidth]);

  // Arrow start: the point of the text box nearest the target, measured after layout.
  const [arrowFrom, setArrowFrom] = useState<[number, number] | null>(null);
  useLayoutEffect(() => {
    if (!role.arrow || !arrowTo || !boxRef.current || !anchorRef.current) return;
    const box = boxRef.current;
    const anchor = anchorRef.current;
    const l = anchor.offsetLeft + box.offsetLeft;
    const t = anchor.offsetTop + box.offsetTop;
    const r = l + box.offsetWidth;
    const b = t + box.offsetHeight;
    const px = Math.min(Math.max(arrowTo[0], l), r);
    const py = Math.min(Math.max(arrowTo[1], t), b);
    // Leave a little air between the letters and the start of the stroke.
    const d = Math.hypot(arrowTo[0] - px, arrowTo[1] - py) || 1;
    const from: [number, number] = [px + ((arrowTo[0] - px) / d) * 24, py + ((arrowTo[1] - py) / d) * 24];
    if (!arrowFrom || Math.abs(arrowFrom[0] - from[0]) > 0.5 || Math.abs(arrowFrom[1] - from[1]) > 0.5) setArrowFrom(from);
  }, [role.arrow, arrowTo, layout, entries, arrowFrom]);

  // Animation: fade + slide up in, fade out. Squeezed if the clip is too short.
  const total = Math.max(1, durationInFrames);
  // 0 frames = no animation on that side (a hard cut on: list items that pop in on the cut).
  const inF = style.animation.in.frames <= 0 ? 0 : Math.max(1, Math.min(style.animation.in.frames, Math.floor(total / 2)));
  const outF = style.animation.out.frames <= 0 ? 0 : Math.max(1, Math.min(style.animation.out.frames, Math.floor(total / 2)));
  const inEase = easingFromName(style.animation.in.ease);
  const outEase = easingFromName(style.animation.out.ease);
  const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;
  const inP = inF ? interpolate(frame, [0, inF], [0, 1], { ...clamp, easing: inEase }) : 1;
  const outP = outF
    ? interpolate(frame, [total - outF, total], [1, 0], {
        ...clamp,
        easing: outEase,
      })
    : 1;
  const opacity = Math.min(inP, outP);
  const slide = (1 - inP) * style.animation.in.distance_px;

  // Safe-zone assertion. Measured from layout offsets (transforms excluded, so in
  // reference pixels), on the first fully-in frame; the slide distance is added to the
  // bottom edge. The box is then scaled to canvas pixels and checked against the
  // scaled safe zone.
  const checkFrame = Math.min(inF, total - 1);
  useLayoutEffect(() => {
    if (frame !== checkFrame) return;
    const box = boxRef.current;
    const anchor = anchorRef.current;
    if (!box || !anchor || !layout) return;
    const k = designScale(style);
    const left = anchor.offsetLeft + box.offsetLeft;
    const top = anchor.offsetTop + box.offsetTop;
    const measured = {
      left: left * k,
      top: top * k,
      right: (left + box.offsetWidth) * k,
      bottom: (top + box.offsetHeight + style.animation.in.distance_px) * k,
    };
    const v = safeZoneViolations(measured, style);
    const r = (n: number) => Math.round(n);
    const boxStr = `x=${r(measured.left)}..${r(measured.right)} y=${r(measured.top)}..${r(measured.bottom)}`;
    if (v.length)
      warn(`SAFE_ZONE_VIOLATION type=${type} preset=${presetName} box ${boxStr}: ${v.join("; ")}`);
    else console.log(`[cf-overlay] SAFE_ZONE_OK type=${type} preset=${presetName} box ${boxStr}`);
    if (layout.wordOverflow)
      warn(
        `TEXT_OVERFLOW more than ${role.maxLines ?? style.typography.max_lines} lines of ${role.maxWordsPerLine ?? style.typography.max_words_per_line} words; extra words folded into the last line`,
      );
    if (layout.shrunk)
      warn(`FONT_SHRUNK ${role.size}px -> ${layout.fontSize}px to fit the safe-zone width`);
    if (titleLayout?.shrunk && role.title)
      warn(`FONT_SHRUNK title ${role.title.size}px -> ${titleLayout.fontSize}px to fit the safe-zone width`);
    if (!face.known) warn(`FONT_FALLBACK "${role.family}" is not a bundled Google font`);
  }, [frame, checkFrame, style, type, layout, titleLayout, face.known, role, presetName]);

  if (!layout) return <AbsoluteFill />;
  // Text blocks top to bottom: the title (when the role has one and the text a blank line), then the body.
  const blocks: { lines: string[]; fontSize: number; lineHeight: number; gapAfter: number }[] = [
    ...(titleLayout && role.title
      ? [{ lines: titleLayout.lines, fontSize: titleLayout.fontSize, lineHeight: role.title.lineHeight, gapAfter: role.title.gap }]
      : []),
    { lines: layout.lines, fontSize: layout.fontSize, lineHeight: role.lineHeight ?? 1.18, gapAfter: 0 },
  ];
  const allRuns = marks.marked
    ? lineRuns(blocks.flatMap((b) => b.lines), marks.words, (t) => applyCase(t, role.case))
    : null;
  let runOffset = 0;
  const blockRuns = blocks.map((b) => {
    const r = allRuns ? allRuns.slice(runOffset, runOffset + b.lines.length) : null;
    runOffset += b.lines.length;
    return r;
  });

  // Everything below is in reference pixels; the design div scales it to the canvas.
  const scale = designScale(style);
  const { width: W, height: H } = referenceSize(style);
  const x = role.x ?? style.safe_zone.left;
  const anchorStyle: React.CSSProperties = (() => {
    switch (role.anchor) {
      case "center":
        // Zero-height full-width row at y: the box is centred on (width/2, y).
        return { left: 0, top: role.y, width: W, height: 0, alignItems: "center", justifyContent: "center" };
      case "top-center":
        return { left: 0, top: role.y, width: W, alignItems: "flex-start", justifyContent: "center" };
      case "bottom-center":
        return { left: 0, bottom: H - role.y, width: W, alignItems: "flex-end", justifyContent: "center" };
      case "bottom-left":
        return { left: x, bottom: H - role.y, alignItems: "flex-end" };
      case "middle-left":
        return { left: x, top: role.y, height: 0, alignItems: "center" };
      case "top-right":
        return { right: W - (role.x ?? W - style.safe_zone.right), top: role.y, alignItems: "flex-start" };
      case "top-left":
      default:
        return { left: x, top: role.y, alignItems: "flex-start" };
    }
  })();

  const centered = role.align === "center";
  const rightAligned = role.align === "right";
  const bd = role.backdrop;
  const rule = role.rule;
  const rulePos = rule?.position ?? "above";
  const ruleWidth = rule ? (rule.width === "text" ? layout.width : rule.width) : 0;
  const orn = role.ornament ?? null;
  const ruleEl = rule ? (
    rule.kind === "squiggle" ? (
      <div style={{ marginTop: rulePos === "below" ? rule.gap : 0, marginBottom: rulePos === "above" ? rule.gap : 0 }}>
        <Squiggle width={ruleWidth} thickness={rule.thickness} color={rule.color} />
      </div>
    ) : (
      <div
        style={{
          width: ruleWidth,
          height: rule.thickness,
          marginTop: rulePos === "below" ? rule.gap : 0,
          marginBottom: rulePos === "above" ? rule.gap : 0,
          backgroundColor: rule.color,
          boxShadow: "0 1px 4px rgba(0,0,0,0.35)",
        }}
      />
    )
  ) : null;

  return (
    // No background anywhere: everything outside the text box stays transparent.
    <AbsoluteFill>
      <div
        style={{
          position: "absolute",
          left: 0,
          top: 0,
          width: W,
          height: H,
          transform: scale !== 1 ? `scale(${scale})` : undefined,
          transformOrigin: "0 0",
        }}
      >
        {role.arrow && arrowTo && arrowFrom && showDecor ? (
          <div style={{ opacity }}>
            <Arrow from={arrowFrom} to={arrowTo} color={role.arrow.color} thickness={role.arrow.thickness} W={W} H={H} />
          </div>
        ) : null}
        <div
          ref={anchorRef}
          style={{
            position: "absolute",
            display: "flex",
            ...anchorStyle,
            opacity,
            transform: `translateY(${slide}px)`,
          }}
        >
          <div
            ref={boxRef}
            style={{
              position: "relative",
              flexShrink: 0,
              display: "flex",
              flexDirection: "column",
              alignItems: centered ? "center" : rightAligned ? "flex-end" : "flex-start",
              padding: bd ? `${bd.padY}px ${bd.padX}px` : 0,
              boxShadow: showBackground && bd?.shadow ? bd.shadow : undefined,
              paddingLeft: (bd?.padX ?? 0) + (role.bar ? role.bar.width + role.bar.gap : 0),
              borderRadius: bd?.radius,
              backgroundColor: showBackground ? bd?.color : undefined,
              isolation: "isolate",
              transform: role.rotate ? `rotate(${role.rotate}deg)` : undefined,
              transformOrigin: centered ? "50% 50%" : "0% 100%",
            }}
          >
            {role.scrim && showBackground ? (
              // Feathered dark ellipse ~1.6x the text box (plus a margin for flat
              // labels), blurred, so bright sky or stone drops under the text.
              <div
                style={{
                  position: "absolute",
                  left: "calc(-30% - 50px)",
                  top: "calc(-30% - 50px)",
                  width: "calc(160% + 100px)",
                  height: "calc(160% + 100px)",
                  zIndex: -1,
                  pointerEvents: "none",
                  background: `radial-gradient(ellipse closest-side at 50% 50%, rgba(0,0,0,${0.6 * role.scrim}) 0%, rgba(0,0,0,${0.45 * role.scrim}) 45%, rgba(0,0,0,0) 100%)`,
                  filter: "blur(48px)",
                }}
              />
            ) : null}
            {role.bar && showDecor ? (
              <div
                style={{
                  position: "absolute",
                  left: bd?.padX ?? 0,
                  top: bd?.padY ?? 0,
                  bottom: bd?.padY ?? 0,
                  width: role.bar.width,
                  backgroundColor: role.bar.color,
                  boxShadow: "0 1px 6px rgba(0,0,0,0.25)",
                }}
              />
            ) : null}
            {rule && rulePos === "above" ? <div style={{ visibility: showDecor ? "visible" : "hidden" }}>{ruleEl}</div> : null}
            {entries && role.list ? (
              <ListBlock
                entries={entries}
                list={role.list}
                role={role}
                faceCss={face.css}
                titleCss={titleFace.css}
                titleWeight={titleWeight}
                defaultColor={role.color ?? style.colors.text}
                showGlyphs={showGlyphs}
                showBackground={showBackground}
              />
            ) : (
            <div style={{ display: "flex", alignItems: "center", gap: role.ornament?.gap ?? 0 }}>
                {orn && orn.side !== "after" ? <OrnamentSvg o={orn} hidden={!showDecor} /> : null}
                <div style={{ display: "flex", flexDirection: "column", alignItems: centered ? "center" : rightAligned ? "flex-end" : "flex-start" }}>
                  {blocks.map((blk, bi) => {
                    const runs = blockRuns[bi];
                    return (
                    <div
                      key={bi}
                      style={{
                        display: "flex",
                        flexDirection: "column",
                        alignItems: centered ? "center" : rightAligned ? "flex-end" : "flex-start",
                        rowGap: role.lineBox?.gap ?? 0,
                        fontFamily: face.css,
                        fontWeight: role.weight,
                        fontStyle: role.italic ? "italic" : "normal",
                        fontSize: blk.fontSize,
                        lineHeight: blk.lineHeight,
                        marginBottom: blk.gapAfter || undefined,
                        letterSpacing: tracking ? `${tracking}em` : undefined,
                        textAlign: centered ? "center" : rightAligned ? "right" : "left",
                        filter: showDecor ? role.filter : undefined,
                      }}
                    >
                      {blk.lines.map((line, i) => (
                        <div
                          key={i}
                          style={{
                            whiteSpace: "nowrap",
                            // Centred tracked text: letter-spacing trails the last glyph, so
                            // pad the left by the same amount to keep it optically centred.
                            paddingLeft: centered && tracking > 0 ? `${tracking}em` : 0,
                            position: "relative",
                            ...(role.lineBox
                              ? {
                                  backgroundColor: showBackground ? role.lineBox.color : undefined,
                                  borderRadius: role.lineBox.radius,
                                  padding: `${role.lineBox.padY}px ${role.lineBox.padX}px`,
                                  paddingLeft: role.lineBox.padX + (centered && tracking > 0 ? tracking * blk.fontSize : 0),
                                }
                              : {}),
                          }}
                        >
                          {role.stroke && showDecor ? (
                            // Stroked copy under the fill: the stroke is centred on the
                            // outline, so 2x width leaves `width` px outside the glyph.
                            <span
                              aria-hidden
                              style={{
                                position: "absolute",
                                left: 0,
                                right: 0,
                                top: 0,
                                bottom: 0,
                                paddingLeft: "inherit",
                                paddingTop: "inherit",
                                color: role.stroke.color,
                                ...(role.stroke.round
                                  ? { textShadow: [roundOutline(role.stroke.width, role.stroke.color), role.shadow].filter(Boolean).join(", ") }
                                  : {
                                      WebkitTextStroke: `${2 * role.stroke.width}px ${role.stroke.color}`,
                                      textShadow: role.shadow ?? undefined,
                                    }),
                                whiteSpace: "nowrap",
                              }}
                            >
                              {line}
                            </span>
                          ) : null}
                          <span
                            style={{
                              position: "relative",
                              visibility: showGlyphs ? "visible" : "hidden",
                              ...(role.gradient
                                ? {
                                    backgroundImage: role.gradient,
                                    WebkitBackgroundClip: "text",
                                    backgroundClip: "text",
                                    color: "transparent",
                                  }
                                : {
                                    color: role.color ?? style.colors.text,
                                    textShadow: role.stroke || !showDecor ? undefined : (role.shadow ?? undefined),
                                  }),
                            }}
                          >
                            {runs
                              ? runs[i].map((r, j) => (
                                  <span key={j} style={r.c ? { color: r.c } : undefined}>
                                    {r.t}
                                  </span>
                                ))
                              : line}
                          </span>
                        </div>
                      ))}
                    </div>
                    );
                  })}
                </div>
                {orn && orn.side !== "before" ? <OrnamentSvg o={orn} hidden={!showDecor} /> : null}
              </div>
            )}
            {rule && rulePos === "below" ? <div style={{ visibility: showDecor ? "visible" : "hidden" }}>{ruleEl}</div> : null}
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};
