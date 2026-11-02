import { useT, type Problem } from "./i18n";

export function ErrorLine({ error }: { error: Problem | null }) {
  const t = useT();
  return error ? <p className="error">{t.problem(error)}</p> : null;
}
