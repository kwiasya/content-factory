import { useState } from "react";
import type { Chapter, Peak } from "./api";
import { seconds } from "./format";

const W = 600;
const H = 120;
const AXIS = 18;

interface Props {
  duration: number;
  peaks: Peak[];
  chapters: Chapter[];
  onSeek?: (s: number) => void;
}

export function Heatmap({ duration, peaks, chapters, onSeek }: Props) {
  const [hover, setHover] = useState<Peak | null>(null);
  const top = Math.max(...peaks.map((p) => p.value), 0) || 1;
  const x = (s: number) => (Math.min(Math.max(s, 0), duration) / duration) * W;
  const plot = H - AXIS;
  const ticks = Array.from({ length: 5 }, (_, i) => (duration * i) / 4);

  return (
    <figure className="heatmap">
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Heatmap peaks over the video's duration">
        <rect x={0} y={0} width={W} height={plot} className="heatmap-bg" />
        {chapters.map((c) => (
          <line key={`c${c.start_s}`} x1={x(c.start_s)} x2={x(c.start_s)} y1={0} y2={plot} className="heatmap-chapter">
            <title>{`${seconds(c.start_s)} ${c.title}`}</title>
          </line>
        ))}
        {peaks.map((p) => {
          const end = p.end_s ?? p.start_s + 1;
          const h = (p.value / top) * (plot - 4);
          return (
            <rect
              key={`p${p.start_s}`}
              x={x(p.start_s)}
              y={plot - h}
              width={Math.max(x(end) - x(p.start_s), 3)}
              height={h}
              className={hover === p ? "heatmap-bar active" : "heatmap-bar"}
              onMouseEnter={() => setHover(p)}
              onMouseLeave={() => setHover(null)}
              onClick={() => onSeek?.(p.start_s)}
            >
              <title>{`${seconds(p.start_s)}–${seconds(p.end_s)}${p.quote ? `: ${p.quote}` : ""}`}</title>
            </rect>
          );
        })}
        <line x1={0} x2={W} y1={plot} y2={plot} className="heatmap-axis" />
        {ticks.map((t, i) => (
          <text
            key={t}
            x={x(t)}
            y={H - 4}
            className="heatmap-tick"
            textAnchor={i === 0 ? "start" : i === ticks.length - 1 ? "end" : "middle"}
          >
            {seconds(t)}
          </text>
        ))}
      </svg>
      <figcaption className="muted">
        {hover ? (
          <>
            <strong>
              {seconds(hover.start_s)}–{seconds(hover.end_s)}
            </strong>{" "}
            {hover.quote ? `«${hover.quote}»` : "no speech in this peak"}
          </>
        ) : (
          "Most replayed moments (bar height: replay strength); hover a bar for its quote, click to seek."
        )}
      </figcaption>
    </figure>
  );
}
