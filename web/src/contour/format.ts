export function outlierText(score: number | null | undefined): string {
  return score === null || score === undefined ? "—" : `${score.toFixed(1)}x`;
}

export function viewsText(views: number | null | undefined): string {
  if (views === null || views === undefined) {
    return "—";
  }
  if (views >= 1_000_000) {
    return `${(views / 1_000_000).toFixed(1)}M`;
  }
  if (views >= 1_000) {
    return `${(views / 1_000).toFixed(1)}K`;
  }
  return String(views);
}

export function seconds(s: number | null | undefined): string {
  if (s === null || s === undefined) {
    return "—";
  }
  const total = Math.round(s);
  const m = Math.floor(total / 60);
  return `${m}:${String(total % 60).padStart(2, "0")}`;
}

export function plain(value: unknown): string {
  if (value === null || value === undefined || value === "") {
    return "—";
  }
  return typeof value === "string" ? value : String(value);
}
