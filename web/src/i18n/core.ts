export type Plural = { one: string; few?: string; many: string };
export type Entry = string | Plural;
export type Params = Record<string, unknown>;

export function pluralForm(lang: string, n: number): keyof Plural {
  if (lang !== "ru") {
    return n === 1 ? "one" : "many";
  }
  if (!Number.isInteger(n)) {
    return "few";
  }
  const mod10 = Math.abs(n) % 10;
  const mod100 = Math.abs(n) % 100;
  if (mod10 === 1 && mod100 !== 11) {
    return "one";
  }
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) {
    return "few";
  }
  return "many";
}

export function pick(entry: Entry, lang: string, params: Params): string {
  if (typeof entry === "string") {
    return entry;
  }
  const n = Number(params.n ?? 0);
  const form = pluralForm(lang, n);
  return (form === "few" ? (entry.few ?? entry.many) : entry[form]) ?? entry.many;
}

export function splitTemplate(template: string): string[] {
  return template.split(/\{(\w+)\}/);
}

export interface Problem {
  message: string;
  code?: string;
  params?: Params;
}
