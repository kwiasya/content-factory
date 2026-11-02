import { useMemo } from "react";
import DOMPurify from "dompurify";
import { marked } from "marked";
import { CodeEditor } from "./CodeEditor";
import { refExtension } from "./library/marked";

marked.use(refExtension);

function stripFrontmatter(text: string): { front: string | null; body: string } {
  const match = /^---\n([\s\S]*?)\n---\n?/.exec(text);
  return match ? { front: match[1], body: text.slice(match[0].length) } : { front: null, body: text };
}

export function Preview({ text, kind }: { text: string; kind: "markdown" | "json" }) {
  const html = useMemo(() => {
    if (kind !== "markdown") {
      return "";
    }
    const { front, body } = stripFrontmatter(text);
    const rendered = marked.parse(body, { async: false, gfm: true });
    const head = front ? `<pre class="frontmatter">${escapeHtml(front)}</pre>` : "";
    return DOMPurify.sanitize(head + rendered);
  }, [text, kind]);

  if (kind === "json") {
    return <CodeEditor value={text} kind="json" readOnly />;
  }
  return <article className="markdown" dangerouslySetInnerHTML={{ __html: html }} />;
}

function escapeHtml(s: string): string {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}
