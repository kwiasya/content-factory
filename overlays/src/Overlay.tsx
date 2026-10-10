import React, { useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import {
  AbsoluteFill,
  CalculateMetadataFunction,
  interpolate,
  useCurrentFrame,
  useDelayRender,
} from "remotion";
import { cssFontFamily, fontsReady } from "./fonts";
import { layoutText, TextLayout } from "./layout";
import {
  applyCase,
  easingFromName,
  fontRoleFor,
  OverlayProps,
  safeZoneViolations,
} from "./style";

const PAD_X = 28;
const PAD_Y = 16;
const RADIUS = 24;
const LINE_HEIGHT = 1.18;

/** Size, fps and length come from props, so one composition serves every overlay. */
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

export const Overlay: React.FC<OverlayProps> = ({
  text,
  type,
  durationInFrames,
  style,
}) => {
  const frame = useCurrentFrame();
  const boxRef = useRef<HTMLDivElement>(null);
  const anchorRef = useRef<HTMLDivElement>(null);

  const font = style.typography[fontRoleFor(type)];
  const family = cssFontFamily(font.family);
  const pos = style.overlay_positions[type];
  const centered = pos.anchor === "center";

  // Hold the frame until the fonts are in, so line breaks are measured with them.
  const { delayRender, continueRender } = useDelayRender();
  const [fontsLoaded, setFontsLoaded] = useState(false);
  const [handle] = useState(() => delayRender("cf-overlay fonts"));
  useEffect(() => {
    fontsReady.then(() => {
      setFontsLoaded(true);
      continueRender(handle);
    });
  }, [continueRender, handle]);

  // Width the safe zone leaves for the text (pill padding excluded).
  const z = style.safe_zone;
  const boxMaxWidth = centered
    ? style.canvas.width - z.left - z.right
    : style.canvas.width - z.right - (pos.x ?? z.left);
  const layout: TextLayout | null = useMemo(
    () =>
      fontsLoaded
        ? layoutText({
            text: applyCase(text, font.case),
            fontFamily: family.css,
            fontWeight: font.weight,
            fontSize: font.size,
            maxWordsPerLine: style.typography.max_words_per_line,
            maxLines: style.typography.max_lines,
            maxWidth: boxMaxWidth - 2 * PAD_X,
          })
        : null,
    [fontsLoaded, text, font, family.css, style.typography, boxMaxWidth],
  );

  // Animation: fade + slide up in, fade out. Squeezed if the clip is too short.
  const total = Math.max(1, durationInFrames);
  const inF = Math.max(1, Math.min(style.animation.in.frames, Math.floor(total / 2)));
  const outF = Math.max(1, Math.min(style.animation.out.frames, Math.floor(total / 2)));
  const inEase = easingFromName(style.animation.in.ease);
  const outEase = easingFromName(style.animation.out.ease);
  const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;
  const inP = interpolate(frame, [0, inF], [0, 1], { ...clamp, easing: inEase });
  const outP = interpolate(frame, [total - outF, total], [1, 0], {
    ...clamp,
    easing: outEase,
  });
  const opacity = Math.min(inP, outP);
  const slide = (1 - inP) * style.animation.in.distance_px;

  // Safe-zone assertion. Measured from layout offsets (transforms excluded), on
  // the first fully-in frame; the slide distance is added to the bottom edge.
  const checkFrame = Math.min(inF, total - 1);
  useLayoutEffect(() => {
    if (frame !== checkFrame) return;
    const box = boxRef.current;
    const anchor = anchorRef.current;
    if (!box || !anchor || !layout) return;
    const left = anchor.offsetLeft + box.offsetLeft;
    const top = anchor.offsetTop + box.offsetTop;
    const measured = {
      left,
      top,
      right: left + box.offsetWidth,
      bottom: top + box.offsetHeight + style.animation.in.distance_px,
    };
    const v = safeZoneViolations(measured, style);
    const r = (n: number) => Math.round(n);
    const boxStr = `x=${r(measured.left)}..${r(measured.right)} y=${r(measured.top)}..${r(measured.bottom)}`;
    if (v.length) warn(`SAFE_ZONE_VIOLATION type=${type} box ${boxStr}: ${v.join("; ")}`);
    else console.log(`[cf-overlay] SAFE_ZONE_OK type=${type} box ${boxStr}`);
    if (layout.wordOverflow)
      warn(
        `TEXT_OVERFLOW more than ${style.typography.max_lines} lines of ${style.typography.max_words_per_line} words; extra words folded into the last line`,
      );
    if (layout.shrunk)
      warn(`FONT_SHRUNK ${font.size}px -> ${layout.fontSize}px to fit the safe-zone width`);
    if (!family.known)
      warn(`FONT_FALLBACK "${font.family}" is not a bundled Google font`);
  }, [frame, checkFrame, style, type, layout, family.known, font.family, font.size]);

  if (!layout) return <AbsoluteFill />;
  const anchorStyle: React.CSSProperties = centered
    ? {
        // Zero-height full-width row at y: the box is centred on (width/2, y).
        position: "absolute",
        left: 0,
        top: pos.y,
        width: style.canvas.width,
        height: 0,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
      }
    : {
        position: "absolute",
        left: pos.x ?? style.safe_zone.left,
        top: pos.y,
        display: "flex",
        alignItems: "flex-start",
      };

  return (
    // No background anywhere: everything outside the pill stays transparent.
    <AbsoluteFill>
      <div
        ref={anchorRef}
        style={{
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
            padding: `${PAD_Y}px ${PAD_X}px`,
            borderRadius: RADIUS,
            backgroundColor: style.colors.backdrop,
            color: style.colors.text,
            fontFamily: family.css,
            fontWeight: font.weight,
            fontSize: layout.fontSize,
            lineHeight: LINE_HEIGHT,
            textAlign: centered ? "center" : "left",
            textShadow: style.colors.text_shadow
              ? `0 2px 12px ${style.colors.text_shadow}`
              : undefined,
          }}
        >
          {layout.lines.map((line, i) => (
            <div key={i} style={{ whiteSpace: "nowrap" }}>
              {line}
            </div>
          ))}
        </div>
      </div>
    </AbsoluteFill>
  );
};
