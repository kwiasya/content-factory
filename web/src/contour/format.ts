import type { T } from "../i18n";

export function outlierText(score: number | null | undefined, t: T): string {
  if (score === null || score === undefined) {
    return "—";
  }
  const n = new Intl.NumberFormat(t.locale, { minimumFractionDigits: 1, maximumFractionDigits: 1 }).format(score);
  return t("unit.outlier", { n });
}

export function viewsText(views: number | null | undefined, t: T): string {
  if (views === null || views === undefined) {
    return "—";
  }
  return new Intl.NumberFormat(t.locale, { notation: "compact", maximumFractionDigits: 1 }).format(views);
}

export function secondsText(s: number | null | undefined, t: T): string {
  if (s === null || s === undefined) {
    return "—";
  }
  return t("unit.s", { n: new Intl.NumberFormat(t.locale).format(s) });
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
