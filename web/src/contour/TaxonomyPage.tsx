import { useCallback, useState } from "react";
import { contourApi, type TaxonomyChange } from "./api";
import { Cmd, ContourShell, Status } from "./ContourShell";
import { cardHref } from "./routes";
import { useLoad } from "./useLoad";
import { useT, type Problem } from "../i18n";
import { ErrorLine } from "../ErrorLine";

const KINDS = ["hook_category", "storytelling_format", "editing_style", "visual_layout"];

export function TaxonomyPage() {
  const t = useT();
  const [kind, setKind] = useState("");
  const [status, setStatus] = useState("proposed");
  const [result, setResult] = useState<TaxonomyChange | null>(null);
  const [actionError, setActionError] = useState<Problem | null>(null);
  const loader = useCallback(() => contourApi.taxonomy(kind, status), [kind, status]);
  const { data, error, reload } = useLoad(loader);

  const judge = (k: string, value: string, action: "approve" | "reject") => {
    setActionError(null);
    contourApi.judge(k, value, action).then(
      (change) => {
        setResult(change);
        reload();
      },
      setActionError,
    );
  };

  const values = data?.values ?? [];
  const kinds = data?.kinds ?? KINDS;
  const groups = kinds
    .map((k) => ({ kind: k, values: values.filter((v) => v.kind === k) }))
    .filter((g) => g.values.length > 0);

  return (
    <ContourShell active="taxonomy">
      <h1>{t("taxonomy.title")}</h1>
      <p className="muted">{t.rich("taxonomy.intro", { prefix: <code>proposed:</code> })}</p>
      <form className="filters" onSubmit={(e) => e.preventDefault()}>
        <label>
          {t("taxonomy.kind")}
          <select value={kind} onChange={(e) => setKind(e.target.value)}>
            <option value="">{t("common.all")}</option>
            {kinds.map((k) => (
              <option key={k} value={k}>
                {k}
              </option>
            ))}
          </select>
        </label>
        <label>
          {t("taxonomy.status")}
          <select value={status} onChange={(e) => setStatus(e.target.value)}>
            <option value="">{t("common.all")}</option>
            {(data?.statuses ?? ["approved", "proposed", "rejected"]).map((s) => (
              <option key={s} value={s}>
                {t.or(`taxonomy.status.${s}`, s)}
              </option>
            ))}
          </select>
        </label>
      </form>
      {result && (
        <p className="warn-box">
          {t.rich("taxonomy.result", {
            value: (
              <code>
                {result.kind} {result.value}
              </code>
            ),
            status: t(`taxonomy.status.${result.status}`),
          })}
          {result.cards.length > 0 && (
            <>
              {" "}
              {t(result.status === "approved" ? "taxonomy.prefixDropped" : "taxonomy.nowFail")}
              {result.cards.map((c) => (
                <a key={c} href={cardHref(c)} className="card-ref">
                  {c}
                </a>
              ))}
            </>
          )}
        </p>
      )}
      <ErrorLine error={actionError} />
      <Status error={error} loading={data === null && !error} />
      {data && groups.length === 0 && (
        <p className="muted">
          {t(status === "proposed" ? "taxonomy.nothingProposed" : "taxonomy.noValues")}
        </p>
      )}
      {groups.map((g) => (
        <section key={g.kind}>
          <h2 className="section">{g.kind}</h2>
          <table className="contour-table">
            <thead>
              <tr>
                <th>{t("taxonomy.col.value")}</th>
                <th>{t("taxonomy.col.label")}</th>
                <th>{t("taxonomy.col.status")}</th>
                <th>{t("taxonomy.col.source")}</th>
                <th>{t("taxonomy.col.note")}</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {g.values.map((v) => (
                <tr key={v.value}>
                  <td>
                    <code>{v.value}</code>
                  </td>
                  <td>{t.taxonomyLabel(v.kind, v.value, v.label) ?? "—"}</td>
                  <td>
                    <span className={`status-pill tax-${v.status}`}>{t(`taxonomy.status.${v.status}`)}</span>
                  </td>
                  <td className="small">
                    {v.source.startsWith("card:") ? (
                      <a href={cardHref(v.source.slice(5))}>{v.source}</a>
                    ) : (
                      v.source
                    )}
                  </td>
                  <td className="small">{v.note ?? ""}</td>
                  <td>
                    <div className="row-actions">
                      {v.status !== "approved" && (
                        <button onClick={() => judge(v.kind, v.value, "approve")}>{t("taxonomy.approve")}</button>
                      )}
                      {v.status !== "rejected" && (
                        <button onClick={() => judge(v.kind, v.value, "reject")}>{t("taxonomy.reject")}</button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      ))}
      <p className="muted small">
        {t.rich("taxonomy.cli", {
          cmd: <Cmd>python -m cf.research taxonomy approve|reject &lt;kind&gt; &lt;value&gt;</Cmd>,
        })}
      </p>
    </ContourShell>
  );
}
