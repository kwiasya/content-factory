import type { GitState } from "./api";

const SHORT: Record<GitState, string> = {
  clean: "",
  modified: "M",
  added: "A",
  deleted: "D",
  renamed: "R",
  copied: "C",
  untracked: "U",
  ignored: "local",
  conflicted: "!",
};

export function GitBadge({ state, compact = false }: { state: GitState; compact?: boolean }) {
  if (state === "clean") {
    return compact ? null : <span className="badge git-clean">clean</span>;
  }
  return (
    <span className={`badge git-${state}`} title={`git: ${state}`}>
      {compact ? SHORT[state] : state}
    </span>
  );
}
