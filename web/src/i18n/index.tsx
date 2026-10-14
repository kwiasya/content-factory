import { createContext, Fragment, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { pick, splitTemplate, type Params, type Problem } from "./core";
import type { Dict, Key } from "./dict";
import { en } from "./en";
import { ru } from "./ru";
import { TAXONOMY_RU } from "./taxonomy";

export type { Key } from "./dict";
export type { Problem } from "./core";

export type Lang = "en" | "ru";

const DICTS: Record<Lang, Dict> = { en, ru };
const LOCALES: Record<Lang, string> = { en: "en-US", ru: "ru-RU" };
const LANGS: Lang[] = ["en", "ru"];
const STORAGE = "desk.lang";
const DEFAULT: Lang = "en";
const EMPTY_LISTS: Record<string, string> = { format_unknown: "formats", channel_unknown: "channels" };

export interface T {
  (key: Key, params?: Params): string;
  rich(key: Key, nodes: Record<string, ReactNode>): ReactNode;
  or(key: string, fallback: string, params?: Params): string;
  problem(problem: Problem): string;
  taxonomyLabel(kind: string, value: string, label: string | null): string | null;
  lang: Lang;
  locale: string;
}

function value(name: string, params: Params, locale: string): string {
  const v = params[name];
  if (v === undefined || v === null) {
    return `{${name}}`;
  }
  if (name === "n" && typeof v === "number") {
    return new Intl.NumberFormat(locale).format(v);
  }
  return Array.isArray(v) ? v.join(", ") : String(v);
}

function makeT(lang: Lang): T {
  const dict = DICTS[lang];
  const locale = LOCALES[lang];
  const has = (key: string): key is Key => Object.prototype.hasOwnProperty.call(dict, key);
  const render = (key: Key, params: Params = {}) =>
    splitTemplate(pick(dict[key], lang, params))
      .map((part, i) => (i % 2 === 1 ? value(part, params, locale) : part))
      .join("");
  const t = ((key: Key, params?: Params) => render(key, params)) as T;
  t.rich = (key, nodes) =>
    splitTemplate(pick(dict[key], lang, {})).map((part, i) => (
      <Fragment key={i}>{i % 2 === 1 ? (nodes[part] ?? `{${part}}`) : part}</Fragment>
    ));
  t.or = (key, fallback, params) => (has(key) ? render(key, params) : fallback);
  t.problem = (problem) => {
    const key = `err.${problem.code ?? ""}`;
    if (!problem.code || !has(key)) {
      return problem.message;
    }
    const params = { ...(problem.params ?? {}) };
    if (problem.code === "idea_move_not_allowed" && typeof params.status === "string") {
      params.status = t.or(`ideas.status.${params.status}`, params.status);
    }
    const listed = EMPTY_LISTS[problem.code];
    if (listed && Array.isArray(params[listed]) && (params[listed] as unknown[]).length === 0 && has(`${key}_none`)) {
      return render(`${key}_none` as Key, params);
    }
    return render(key, params);
  };
  t.taxonomyLabel = (kind, val, label) => (lang === "ru" ? (TAXONOMY_RU[`${kind}.${val}`] ?? label) : label);
  t.lang = lang;
  t.locale = locale;
  return t;
}

function stored(): Lang {
  try {
    const v = window.localStorage.getItem(STORAGE);
    return v === "ru" || v === "en" ? v : DEFAULT;
  } catch {
    return DEFAULT;
  }
}

interface LangState {
  t: T;
  setLang: (lang: Lang) => void;
}

const Context = createContext<LangState>({ t: makeT(DEFAULT), setLang: () => undefined });

export function LangProvider({ children }: { children: ReactNode }) {
  const [lang, setLang] = useState<Lang>(stored);
  const t = useMemo(() => makeT(lang), [lang]);

  useEffect(() => {
    document.documentElement.lang = lang;
    document.title = t("app.title");
    try {
      window.localStorage.setItem(STORAGE, lang);
    } catch {
      return;
    }
  }, [lang, t]);

  const state = useMemo(() => ({ t, setLang }), [t]);
  return <Context.Provider value={state}>{children}</Context.Provider>;
}

export function useT(): T {
  return useContext(Context).t;
}

export function LangSwitch() {
  const { t, setLang } = useContext(Context);
  return (
    <span className="lang-switch" role="group" aria-label={t("app.language")}>
      {LANGS.map((l) => (
        <button key={l} className={l === t.lang ? "active" : ""} aria-pressed={l === t.lang} onClick={() => setLang(l)}>
          {t(`lang.${l}`)}
        </button>
      ))}
    </span>
  );
}
