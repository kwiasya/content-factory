import { useEffect, useRef } from "react";
import { basicSetup } from "codemirror";
import { EditorState } from "@codemirror/state";
import { EditorView } from "@codemirror/view";
import { json } from "@codemirror/lang-json";
import { markdown } from "@codemirror/lang-markdown";
import { useT } from "./i18n";
import { CODEMIRROR_RU } from "./i18n/codemirror";

interface Props {
  value: string;
  kind: "markdown" | "json";
  readOnly: boolean;
  onChange?: (value: string) => void;
}

export function CodeEditor({ value, kind, readOnly, onChange }: Props) {
  const host = useRef<HTMLDivElement>(null);
  const view = useRef<EditorView | null>(null);
  const changed = useRef(onChange);
  const lang = useT().lang;

  useEffect(() => {
    changed.current = onChange;
  }, [onChange]);

  useEffect(() => {
    if (!host.current) {
      return;
    }
    const editor = new EditorView({
      parent: host.current,
      state: EditorState.create({
        doc: "",
        extensions: [
          basicSetup,
          kind === "json" ? json() : markdown(),
          EditorView.lineWrapping,
          EditorState.phrases.of(lang === "ru" ? CODEMIRROR_RU : {}),
          EditorState.readOnly.of(readOnly),
          EditorView.editable.of(!readOnly),
          EditorView.updateListener.of((update) => {
            if (update.docChanged) {
              changed.current?.(update.state.doc.toString());
            }
          }),
        ],
      }),
    });
    view.current = editor;
    return () => {
      editor.destroy();
      view.current = null;
    };
  }, [kind, readOnly, lang]);

  useEffect(() => {
    const editor = view.current;
    if (editor && editor.state.doc.toString() !== value) {
      editor.dispatch({ changes: { from: 0, to: editor.state.doc.length, insert: value } });
    }
  }, [value, kind, readOnly, lang]);

  return <div className="code" ref={host} />;
}
