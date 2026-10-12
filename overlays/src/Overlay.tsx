import React, { useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import {
  AbsoluteFill,
  CalculateMetadataFunction,
  interpolate,
  useCurrentFrame,
  useDelayRender,
} from "remotion";
import { loadFace } from "./fonts";
import { layoutText, TextLayout } from "./layout";
import { Ornament, resolveRole, RoleStyle } from "./presets";
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
  } else {
    const right = rail ? W - rail.width : W - z.right;
    avail = right - (role.x ?? z.left);
  }
  if (role.maxWidth) avail = Math.min(avail, role.maxWidth);
  const o = role.ornament;
  const extra =
    2 * (role.backdrop?.padX ?? 0) +
    2 * (role.lineBox?.padX ?? 0) +
    (role.bar ? role.bar.width + role.bar.gap : 0) +
    (o ? (o.side === "both" ? 2 : 1) * (ornamentWidth(o) + o.gap) : 0);
  return avail - extra;
};

export const Overlay: React.FC<OverlayProps> = ({
  text,
  type,
  durationInFrames,
  style,
  preset,
  anchor: anchorOverride,
  scrim: scrimOverride,
  layers = "all",
}) => {
  const frame = useCurrentFrame();
  const boxRef = useRef<HTMLDivElement>(null);
  const anchorRef = useRef<HTMLDivElement>(null);

  const presetName = preset ?? style.typography.preset ?? "legacy";
  const role = useMemo(
    () => resolveRole(style, type, presetName, { anchor: anchorOverride, scrim: scrimOverride }),
    [style, type, presetName, anchorOverride, scrimOverride],
  );
  const showGlyphs = layers !== "background";
  const showDecor = layers === "all";
  const showBackground = layers !== "glyphs";
  const face = useMemo(
    () => loadFace(role.family, role.weight, role.italic),
    [role.family, role.weight, role.italic],
  );

  // Hold the frame until the font is in, so line breaks are measured with it.
  const { delayRender, continueRender } = useDelayRender();
  const [fontsLoaded, setFontsLoaded] = useState(false);
  const [handle] = useState(() => delayRender("cf-overlay fonts"));
  useEffect(() => {
    face.ready.then(() => {
      setFontsLoaded(true);
      continueRender(handle);
    });
  }, [continueRender, handle, face]);

  const maxWidth = textMaxWidth(role, style);
  const tracking = role.tracking ?? 0;
  const layout: TextLayout | null = useMemo(
    () =>
      fontsLoaded
        ? layoutText({
            text: applyCase(text, role.case),
            fontFamily: face.css,
            fontWeight: role.weight,
            fontStyle: role.italic ? "italic" : "normal",
            fontSize: role.size,
            letterSpacingEm: tracking,
            maxWordsPerLine: role.maxWordsPerLine ?? style.typography.max_words_per_line,
            maxLines: role.maxLines ?? style.typography.max_lines,
            maxWidth,
            punctuationBreaks: role.punctuationBreaks,
          })
        : null,
    [fontsLoaded, text, role, face.css, tracking, style.typography, maxWidth],
  );

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
    if (!face.known) warn(`FONT_FALLBACK "${role.family}" is not a bundled Google font`);
  }, [frame, checkFrame, style, type, layout, face.known, role, presetName]);

  if (!layout) return <AbsoluteFill />;

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
      case "top-left":
      default:
        return { left: x, top: role.y, alignItems: "flex-start" };
    }
  })();

  const centered = role.align === "center";
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
              alignItems: centered ? "center" : "flex-start",
              padding: bd ? `${bd.padY}px ${bd.padX}px` : 0,
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
            <div style={{ display: "flex", alignItems: "center", gap: role.ornament?.gap ?? 0 }}>
              {orn && orn.side !== "after" ? <OrnamentSvg o={orn} hidden={!showDecor} /> : null}
              <div
                style={{
                  display: "flex",
                  flexDirection: "column",
                  alignItems: centered ? "center" : "flex-start",
                  rowGap: role.lineBox?.gap ?? 0,
                  fontFamily: face.css,
                  fontWeight: role.weight,
                  fontStyle: role.italic ? "italic" : "normal",
                  fontSize: layout.fontSize,
                  lineHeight: role.lineHeight ?? 1.18,
                  letterSpacing: tracking ? `${tracking}em` : undefined,
                  textAlign: centered ? "center" : "left",
                  filter: showDecor ? role.filter : undefined,
                }}
              >
                {layout.lines.map((line, i) => (
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
                            paddingLeft: role.lineBox.padX + (centered && tracking > 0 ? tracking * layout.fontSize : 0),
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
                          WebkitTextStroke: `${2 * role.stroke.width}px ${role.stroke.color}`,
                          textShadow: role.shadow ?? undefined,
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
                      {line}
                    </span>
                  </div>
                ))}
              </div>
              {orn && orn.side !== "before" ? <OrnamentSvg o={orn} hidden={!showDecor} /> : null}
            </div>
            {rule && rulePos === "below" ? <div style={{ visibility: showDecor ? "visible" : "hidden" }}>{ruleEl}</div> : null}
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};
