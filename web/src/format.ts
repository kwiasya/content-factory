import type { T } from "./i18n";

export function formatTime(iso: string, t: T): string {
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleString(t.locale, { dateStyle: "medium", timeStyle: "short" });
}

const UNITS = ["unit.B", "unit.KB", "unit.MB", "unit.GB"] as const;

export function formatSize(bytes: number, t: T): string {
  let value = bytes;
  let unit = 0;
  while (value >= 1024 && unit < UNITS.length - 1) {
    value /= 1024;
    unit += 1;
  }
  const digits = unit === 0 ? 0 : 1;
  const number = new Intl.NumberFormat(t.locale, { minimumFractionDigits: digits, maximumFractionDigits: digits });
  return `${number.format(value)} ${t(UNITS[unit])}`;
}

export function formatNumber(n: number, t: T): string {
  return new Intl.NumberFormat(t.locale).format(n);
}

export function formatDate(iso: string | null | undefined, t: T): string {
  if (!iso) {
    return "—";
  }
  const dateOnly = /^\d{4}-\d{2}-\d{2}$/.test(iso);
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) {
    return iso;
  }
  return d.toLocaleDateString(t.locale, { dateStyle: "medium", timeZone: dateOnly ? "UTC" : undefined });
}
