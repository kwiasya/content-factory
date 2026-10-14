import { useEffect, useId, useState } from "react";
import { useT } from "../i18n";
import { libraryApi, type TagCount } from "./libraryApi";

export function TagEditor({ tags, onChange }: { tags: string[]; onChange: (tags: string[]) => void }) {
  const t = useT();
  const [draft, setDraft] = useState("");
  const [options, setOptions] = useState<TagCount[]>([]);
  const listId = useId();

  useEffect(() => {
    const q = draft.trim();
    if (!q) {
      return;
    }
    let live = true;
    const timer = window.setTimeout(() => {
      libraryApi.tags(q).then(
        (rows) => live && setOptions(rows.filter((r) => !tags.some((x) => x.toLowerCase() === r.tag.toLowerCase()))),
        () => live && setOptions([]),
      );
    }, 150);
    return () => {
      live = false;
      window.clearTimeout(timer);
    };
  }, [draft, tags]);

  const add = (value: string) => {
    const tag = value.trim().replace(/\s+/g, " ");
    setDraft("");
    setOptions([]);
    if (tag && !tags.some((x) => x.toLowerCase() === tag.toLowerCase())) {
      onChange([...tags, tag]);
    }
  };

  return (
    <div className="lib-tags-editor">
      <ul className="lib-chips">
        {tags.map((tag) => (
          <li key={tag} className="lib-chip">
            {tag}
            <button
              className="lib-chip-x"
              aria-label={t("library.card.removeTag", { tag })}
              onClick={() => onChange(tags.filter((x) => x !== tag))}
            >
              ×
            </button>
          </li>
        ))}
      </ul>
      <input
        value={draft}
        list={listId}
        placeholder={t("library.card.addTag")}
        aria-label={t("library.card.addTag")}
        onChange={(e) => setDraft(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter") {
            e.preventDefault();
            add(draft);
          }
        }}
      />
      <datalist id={listId}>
        {(draft.trim() ? options : []).map((o) => (
          <option key={o.tag} value={o.tag}>
            {o.n}
          </option>
        ))}
      </datalist>
    </div>
  );
}
