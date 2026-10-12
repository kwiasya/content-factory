import { useCallback, useState } from "react";
import { contourApi, type TaxonomyChange } from "./api";
import { Cmd, ContourShell, Status } from "./ContourShell";
import { cardHref } from "./routes";
import { useLoad } from "./useLoad";

const KINDS = ["hook_category", "storytelling_format", "editing_style", "visual_layout"];

export function TaxonomyPage() {
  const [kind, setKind] = useState("");
  const [status, setStatus] = useState("proposed");
  const [result, setResult] = useState<TaxonomyChange | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const loader = useCallback(() => contourApi.taxonomy(kind, status), [kind, status]);
  const { data, error, reload } = useLoad(loader);

  const judge = (k: string, value: string, action: "approve" | "reject") => {
    setActionError(null);
    contourApi.judge(k, value, action).then(
      (change) => {
        setResult(change);
        reload();
      },
      (e: Error) => setActionError(e.message),
    );
  };

  const values = data?.values ?? [];
  const kinds = data?.kinds ?? KINDS;
  const groups = kinds
    .map((k) => ({ kind: k, values: values.filter((v) => v.kind === k) }))
    .filter((g) => g.values.length > 0);

  return (
    <ContourShell active="taxonomy">
      <h1>Taxonomy</h1>
      <p className="muted">
        The vocabulary of Reference cards. A <code>proposed:</code> value waits for your decision: approve makes it valid
        and drops the prefix in the cards that proposed it; reject makes those cards fail validation until rewritten.
      </p>
      <form className="filters" onSubmit={(e) => e.preventDefault()}>
        <label>
          Kind
          <select value={kind} onChange={(e) => setKind(e.target.value)}>
            <option value="">all</option>
            {kinds.map((k) => (
              <option key={k} value={k}>
                {k}
              </option>
            ))}
          </select>
        </label>
        <label>
          Status
          <select value={status} onChange={(e) => setStatus(e.target.value)}>
            <option value="">all</option>
            {(data?.statuses ?? ["approved", "proposed", "rejected"]).map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </label>
      </form>
      {result && (
        <p className="warn-box">
          <code>
            {result.kind} {result.value}
          </code>{" "}
          is now {result.status}.
          {result.cards.length > 0 && (
            <>
              {" "}
              {result.status === "approved" ? "Prefix dropped in: " : "These cards now fail validation: "}
              {result.cards.map((c) => (
                <a key={c} href={cardHref(c)} className="card-ref">
                  {c}
                </a>
              ))}
            </>
          )}
        </p>
      )}
      {actionError && <p className="error">{actionError}</p>}
      <Status error={error} loading={data === null && !error} />
      {data && groups.length === 0 && (
        <p className="muted">
          {status === "proposed"
            ? "Nothing awaits approval. New values appear when /analyze-reference saves a card with proposed:<value>."
            : "No values."}
        </p>
      )}
      {groups.map((g) => (
        <section key={g.kind}>
          <h2 className="section">{g.kind}</h2>
          <table className="contour-table">
            <thead>
              <tr>
                <th>Value</th>
                <th>Label</th>
                <th>Status</th>
                <th>Source</th>
                <th>Note</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {g.values.map((v) => (
                <tr key={v.value}>
                  <td>
                    <code>{v.value}</code>
                  </td>
                  <td>{v.label ?? "—"}</td>
                  <td>
                    <span className={`status-pill tax-${v.status}`}>{v.status}</span>
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
                        <button onClick={() => judge(v.kind, v.value, "approve")}>Approve</button>
                      )}
                      {v.status !== "rejected" && <button onClick={() => judge(v.kind, v.value, "reject")}>Reject</button>}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      ))}
      <p className="muted small">
        CLI: <Cmd>python -m cf.research taxonomy approve|reject &lt;kind&gt; &lt;value&gt;</Cmd>
      </p>
    </ContourShell>
  );
}
