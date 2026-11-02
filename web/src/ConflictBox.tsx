import { useT, type Key } from "./i18n";

interface Props {
  title: Key;
  fresh?: string;
  onReload: () => void;
  onOverwrite: () => void;
}

export function ConflictBox({ title, fresh, onReload, onOverwrite }: Props) {
  const t = useT();
  return (
    <div className="conflict">
      <p>
        <strong>{t(title)}</strong> {t("conflict.kept")}
      </p>
      <div className="actions">
        <button onClick={onReload}>{t("conflict.reload")}</button>
        <button onClick={onOverwrite}>{t("conflict.overwrite")}</button>
      </div>
      {fresh !== undefined && (
        <details>
          <summary>{t("conflict.fresh")}</summary>
          <pre>{fresh}</pre>
        </details>
      )}
    </div>
  );
}
