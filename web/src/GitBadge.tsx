import type { GitState } from "./api";
import { useT } from "./i18n";

const SHORT: Partial<Record<GitState, string>> = {
  modified: "M",
  added: "A",
  deleted: "D",
  renamed: "R",
  copied: "C",
  untracked: "U",
  conflicted: "!",
};

export function GitBadge({ state, compact = false }: { state: GitState; compact?: boolean }) {
  const t = useT();
  const label = t(`git.${state}`);
  if (state === "clean") {
    return compact ? null : <span className="badge git-clean">{label}</span>;
  }
  return (
    <span className={`badge git-${state}`} title={t("git.title", { state: label })}>
      {compact ? (SHORT[state] ?? t("git.short.ignored")) : label}
    </span>
  );
}
