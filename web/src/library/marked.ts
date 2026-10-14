import type { MarkedExtension, Tokens } from "marked";
import { libraryRefHref } from "../shell/routes";
import { CATEGORIES } from "./refs";

const START = new RegExp(`(^|[\\s(\\[«"'])@(?:${CATEGORIES.join("|")})\\/`, "u");
const TOKEN = new RegExp(`^@(?:${CATEGORIES.join("|")})\\/[\\p{L}\\p{N}-]+`, "u");

function escape(s: string): string {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

export const refExtension: MarkedExtension = {
  extensions: [
    {
      name: "assetRef",
      level: "inline",
      start(src: string) {
        const m = START.exec(src);
        return m ? m.index + m[1].length : undefined;
      },
      tokenizer(src: string) {
        const m = TOKEN.exec(src);
        return m ? { type: "assetRef", raw: m[0], ref: m[0] } : undefined;
      },
      renderer(token: Tokens.Generic) {
        const ref = token.ref as string;
        return `<a class="ref" href="${escape(libraryRefHref(ref))}">${escape(ref)}</a>`;
      },
    },
  ],
};
