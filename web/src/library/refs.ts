export const CATEGORIES = ["sfx", "meme", "img", "emoji", "face", "bg", "footage", "fx", "music", "font", "template"] as const;

const CATS = CATEGORIES.join("|");

export const REF_SOURCE = `(^|[\\s(\\[«"'])(@(?:${CATS})\\/[\\p{L}\\p{N}-]+)`;

export function refRegExp(): RegExp {
  return new RegExp(REF_SOURCE, "gu");
}

export interface FoundRef {
  ref: string;
  from: number;
  to: number;
}

export function findRefs(text: string, offset = 0): FoundRef[] {
  const out: FoundRef[] = [];
  for (const m of text.matchAll(refRegExp())) {
    const from = (m.index ?? 0) + m[1].length;
    out.push({ ref: m[2], from: offset + from, to: offset + from + m[2].length });
  }
  return out;
}
