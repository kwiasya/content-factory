import { useMemo } from "react";
import DOMPurify from "dompurify";
import { marked } from "marked";
import { useT } from "../i18n";

interface Heading {
  id: string;
  level: number;
  text: string;
}

function render(text: string, prefix: string): { html: string; toc: Heading[] } {
  const raw = marked.parse(text, { async: false, gfm: true });
  const dom = new DOMParser().parseFromString(DOMPurify.sanitize(raw), "text/html");
  const toc: Heading[] = [];
  dom.body.querySelectorAll("h1, h2, h3").forEach((h, i) => {
    const id = `${prefix}-h${i}`;
    h.id = id;
    toc.push({ id, level: Number(h.tagName[1]), text: h.textContent ?? "" });
  });
  return { html: dom.body.innerHTML, toc };
}

export function TocDocument({ text, prefix }: { text: string; prefix: string }) {
  const t = useT();
  const { html, toc } = useMemo(() => render(text, prefix), [text, prefix]);
  const jump = (id: string) => document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });

  return (
    <div className="toc-doc">
      {toc.length > 1 && (
        <nav className="toc">
          <h3>{t("research.contents")}</h3>
          <ul>
            {toc.map((h) => (
              <li key={h.id} className={`toc-${h.level}`}>
                <button className="link" onClick={() => jump(h.id)}>
                  {h.text}
                </button>
              </li>
            ))}
          </ul>
        </nav>
      )}
      <article className="markdown" dangerouslySetInnerHTML={{ __html: html }} />
    </div>
  );
}
