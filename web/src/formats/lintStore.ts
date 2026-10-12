import { useSyncExternalStore } from "react";
import { formatsApi } from "./api";

let counts: Record<string, number> = {};
let requested = false;
const listeners = new Set<() => void>();

export function refreshLintSummary(): void {
  requested = true;
  formatsApi.lintSummary().then(
    (next) => {
      counts = next;
      listeners.forEach((l) => l());
    },
    () => undefined,
  );
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  if (!requested) {
    refreshLintSummary();
  }
  return () => listeners.delete(listener);
}

export function useLintCount(skill: string | null): number {
  return useSyncExternalStore(subscribe, () => (skill ? (counts[skill] ?? 0) : 0));
}
