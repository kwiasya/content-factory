import type { Completion, CompletionContext, CompletionResult } from "@codemirror/autocomplete";
import { markdownLanguage } from "@codemirror/lang-markdown";
import { RangeSetBuilder, StateEffect, type Extension } from "@codemirror/state";
import {
  closeHoverTooltips,
  Decoration,
  EditorView,
  hoverTooltip,
  ViewPlugin,
  type DecorationSet,
  type Tooltip,
  type ViewUpdate,
} from "@codemirror/view";
import { mediaUrl } from "../api";
import type { T } from "../i18n";
import { libraryHref } from "../shell/routes";
import { libraryApi, type AssetCard, type CheckResult } from "./libraryApi";
import { findRefs, type FoundRef } from "./refs";

const cache = new Map<string, CheckResult>();
const pending = new Set<string>();
const refreshed = StateEffect.define<null>();

function el<K extends keyof HTMLElementTagNameMap>(tag: K, cls?: string, text?: string): HTMLElementTagNameMap[K] {
  const node = document.createElement(tag);
  if (cls) node.className = cls;
  if (text !== undefined) node.textContent = text;
  return node;
}

function preview(asset: AssetCard): HTMLElement | null {
  if (asset.kind === "audio" && asset.media.original) {
    const audio = el("audio");
    audio.controls = true;
    audio.preload = "none";
    audio.src = mediaUrl(asset.media.original);
    return audio;
  }
  const poster = asset.media.poster ?? asset.media.png ?? (asset.kind === "image" ? asset.media.original : null);
  if (poster) {
    const img = el("img");
    img.src = mediaUrl(poster);
    img.alt = asset.ref;
    return img;
  }
  return null;
}

function infoNode(asset: AssetCard, t: T): HTMLElement {
  const box = el("div", "cm-ref-info");
  const media = preview(asset);
  if (media) box.append(media);
  box.append(el("code", undefined, asset.ref));
  const caption = asset.caption ?? asset.agent_caption;
  if (caption) box.append(el("p", undefined, caption));
  const tags = [...asset.tags, ...asset.agent_tags.filter((x) => !asset.tags.includes(x))];
  if (tags.length) box.append(el("p", "cm-ref-tags", tags.join(" · ")));
  box.append(el("span", `lib-badge rights-${asset.rights}`, t(`library.rights.${asset.rights}`)));
  return box;
}

function refSource(t: T) {
  return async (context: CompletionContext): Promise<CompletionResult | null> => {
    const word = context.matchBefore(/@[\p{L}\p{N}/-]*$/u);
    if (!word) return null;
    const before = word.from > 0 ? context.state.sliceDoc(word.from - 1, word.from) : "";
    if (before && !/[\s([«"']/u.test(before)) return null;
    if (word.to - word.from < 2 && !context.explicit) return null;
    let found: AssetCard[];
    try {
      found = await libraryApi.suggest(word.text.slice(1), 20);
    } catch {
      return null;
    }
    const options: Completion[] = found.map((a) => ({
      label: a.ref,
      detail: a.caption ?? a.agent_caption ?? undefined,
      type: "variable",
      info: () => infoNode(a, t),
    }));
    return { from: word.from, options, filter: false, validFor: /^@[\p{L}\p{N}/-]*$/u };
  };
}

function visibleRefs(view: EditorView): FoundRef[] {
  const out: FoundRef[] = [];
  for (const { from, to } of view.visibleRanges) {
    const start = view.state.doc.lineAt(from).from;
    out.push(...findRefs(view.state.sliceDoc(start, to), start));
  }
  return out;
}

function decorate(view: EditorView): DecorationSet {
  const builder = new RangeSetBuilder<Decoration>();
  const seen = new Set<number>();
  for (const r of visibleRefs(view)) {
    if (seen.has(r.from)) continue;
    seen.add(r.from);
    const state = cache.get(r.ref);
    const broken = state !== undefined && !state.ok;
    builder.add(r.from, r.to, Decoration.mark({
      class: broken ? "cm-ref cm-ref-broken" : "cm-ref",
      attributes: { "data-ref": r.ref },
    }));
  }
  return builder.finish();
}

const decorations = ViewPlugin.fromClass(
  class {
    decorations: DecorationSet;
    timer = 0;

    constructor(view: EditorView) {
      this.decorations = decorate(view);
      this.schedule(view);
    }

    update(update: ViewUpdate) {
      const fresh = update.transactions.some((tr) => tr.effects.some((e) => e.is(refreshed)));
      if (update.docChanged || update.viewportChanged || fresh) {
        this.decorations = decorate(update.view);
      }
      if (update.docChanged || update.viewportChanged) {
        this.schedule(update.view);
      }
    }

    schedule(view: EditorView) {
      window.clearTimeout(this.timer);
      this.timer = window.setTimeout(() => this.check(view), 300);
    }

    async check(view: EditorView) {
      const unknown = [...new Set(visibleRefs(view).map((r) => r.ref))].filter((r) => !cache.has(r) && !pending.has(r));
      if (!unknown.length) return;
      unknown.forEach((r) => pending.add(r));
      try {
        const result = await libraryApi.check(unknown.slice(0, 200));
        for (const [ref, state] of Object.entries(result)) cache.set(ref, state);
      } catch {
        return;
      } finally {
        unknown.forEach((r) => pending.delete(r));
      }
      view.dispatch({ effects: refreshed.of(null) });
    }

    destroy() {
      window.clearTimeout(this.timer);
    }
  },
  { decorations: (v) => v.decorations },
);

function refAt(view: EditorView, pos: number): FoundRef | null {
  const line = view.state.doc.lineAt(pos);
  return findRefs(line.text, line.from).find((r) => r.from <= pos && pos <= r.to) ?? null;
}

async function stateOf(ref: string): Promise<CheckResult | null> {
  const known = cache.get(ref);
  if (known) return known;
  try {
    const result = await libraryApi.check([ref]);
    const state = result[ref];
    if (state) cache.set(ref, state);
    return state ?? null;
  } catch {
    return null;
  }
}

function hover(t: T) {
  return hoverTooltip(async (view, pos): Promise<Tooltip | null> => {
    const found = refAt(view, pos);
    if (!found) return null;
    const state = await stateOf(found.ref);
    if (!state) return null;
    let dom: HTMLElement;
    if (state.ok) {
      let asset: AssetCard;
      try {
        asset = await libraryApi.asset(state.id);
      } catch {
        return null;
      }
      dom = infoNode(asset, t);
      const link = el("a", "cm-ref-open", t("library.openInLibrary"));
      link.href = libraryHref(asset.id);
      dom.append(link);
    } else {
      dom = el("div", "cm-ref-info");
      dom.append(el("p", "cm-ref-missing", t("library.noSuchAsset", { ref: found.ref })));
      if (state.suggestions.length) {
        dom.append(el("p", "cm-ref-hint", t("library.didYouMean")));
        const list = el("div", "cm-ref-suggestions");
        for (const s of state.suggestions.slice(0, 5)) {
          const b = el("button", undefined, s);
          b.addEventListener("mousedown", (e) => {
            e.preventDefault();
            const now = refAt(view, found.from);
            if (now) view.dispatch({ changes: { from: now.from, to: now.to, insert: s }, effects: closeHoverTooltips });
          });
          list.append(b);
        }
        dom.append(list);
      }
    }
    return { pos: found.from, end: found.to, above: true, create: () => ({ dom }) };
  });
}

const clickThrough = EditorView.domEventHandlers({
  mousedown(event, view) {
    if (!(event.metaKey || event.ctrlKey)) return false;
    const pos = view.posAtCoords({ x: event.clientX, y: event.clientY });
    if (pos === null) return false;
    const found = refAt(view, pos);
    if (!found) return false;
    event.preventDefault();
    stateOf(found.ref).then((state) => {
      if (state?.ok) window.location.hash = libraryHref(state.id);
    });
    return true;
  },
});

const theme = EditorView.baseTheme({
  ".cm-ref": { textDecoration: "underline dotted", textUnderlineOffset: "3px", color: "var(--accent)" },
  ".cm-ref-broken": { textDecoration: "underline wavy var(--del-text)", color: "inherit" },
  ".cm-ref-info": { padding: "6px 8px", maxWidth: "280px", display: "flex", flexDirection: "column", gap: "4px" },
  ".cm-ref-info img": { maxWidth: "240px", maxHeight: "160px", background: "#202020", borderRadius: "4px" },
  ".cm-ref-info p": { margin: "0" },
  ".cm-ref-tags": { color: "var(--muted)", fontSize: "12px" },
  ".cm-ref-suggestions": { display: "flex", flexDirection: "column", gap: "2px", alignItems: "flex-start" },
});

export function refsExtension(t: T): Extension {
  return [markdownLanguage.data.of({ autocomplete: refSource(t) }), decorations, hover(t), clickThrough, theme];
}
