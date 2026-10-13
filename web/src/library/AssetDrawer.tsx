import { useEffect, useRef, useState, type KeyboardEvent as ReactKeyboardEvent, type ReactNode } from "react";
import { mediaUrl } from "../api";
import { ErrorLine } from "../ErrorLine";
import { formatSize } from "../format";
import { useT, type Problem } from "../i18n";
import { Badges, formatDuration } from "./AssetCard";
import { FontFaces, FontSample } from "./FontSample";
import { libraryApi, type AssetCard, type AuthorFields, type Rights } from "./libraryApi";
import { TagEditor } from "./TagEditor";

const BROWSER_CODECS = new Set(["h264", "vp8", "vp9", "av1", "hevc"]);

function LargePreview({ asset }: { asset: AssetCard }) {
  if (asset.kind === "audio" && asset.media.original) {
    return <audio controls preload="none" src={mediaUrl(asset.media.original)} />;
  }
  if (asset.kind === "font") {
    return <FontSample asset={asset} large />;
  }
  if (asset.kind === "video") {
    const codec = asset.variants?.[0]?.codec ?? null;
    const src = asset.media.original && codec && BROWSER_CODECS.has(codec) && !asset.file.name.endsWith(".gif")
      ? asset.media.original
      : asset.media.preview;
    return src ? <video key={src} controls loop playsInline src={mediaUrl(src)} poster={asset.media.poster ? mediaUrl(asset.media.poster) : undefined} /> : null;
  }
  if (asset.kind === "image") {
    const src = asset.media.png ?? asset.media.original;
    return src ? <img src={mediaUrl(src)} alt={asset.ref} /> : null;
  }
  return null;
}

function CopyRef({ value }: { value: string }) {
  const t = useT();
  const [copied, setCopied] = useState(false);
  return (
    <button
      className="lib-copy"
      onClick={() => {
        navigator.clipboard?.writeText(value).then(() => {
          setCopied(true);
          window.setTimeout(() => setCopied(false), 1200);
        }, () => undefined);
      }}
    >
      {t(copied ? "library.card.copied" : "library.card.copy")}
    </button>
  );
}

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <>
      <dt>{label}</dt>
      <dd>{children}</dd>
    </>
  );
}

export function AssetDrawer({ id, onClose, onChanged, onReveal }: {
  id: string;
  onClose: () => void;
  onChanged: (asset: AssetCard) => void;
  onReveal: (asset: AssetCard) => void;
}) {
  const t = useT();
  const [asset, setAsset] = useState<AssetCard | null>(null);
  const [error, setError] = useState<Problem | null>(null);
  const [fieldError, setFieldError] = useState<{ field: string; problem: Problem } | null>(null);
  const [caption, setCaption] = useState("");
  const [name, setName] = useState("");
  const latest = useRef(0);

  useEffect(() => {
    let live = true;
    libraryApi.asset(id).then(
      (a) => {
        if (!live) return;
        setAsset(a);
        setCaption(a.caption ?? "");
        setName(a.author_name ?? "");
        setError(null);
        setFieldError(null);
      },
      (e: Error) => live && setError(e),
    );
    return () => {
      live = false;
    };
  }, [id]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  if (!asset) {
    return (
      <aside className="lib-drawer" aria-label={t("library.card.title")}>
        <button className="lib-close" onClick={onClose} aria-label={t("library.close")}>×</button>
        {error ? <ErrorLine error={error} /> : <p className="muted">{t("common.loading")}</p>}
      </aside>
    );
  }

  const save = (field: keyof AuthorFields, value: AuthorFields[keyof AuthorFields]) => {
    setFieldError(null);
    const seq = ++latest.current;
    libraryApi.setAuthor(asset.id, { [field]: value }).then(
      (a) => {
        if (seq !== latest.current) return;
        setAsset(a);
        setCaption(a.caption ?? "");
        setName(a.author_name ?? "");
        onChanged(a);
      },
      (e: Error) => setFieldError({ field, problem: e }),
    );
  };
  const errorFor = (field: string) => (fieldError?.field === field ? <ErrorLine error={fieldError.problem} /> : null);
  const saveCaption = () => {
    if (caption.trim() !== (asset.caption ?? "")) save("caption", caption.trim() || null);
  };
  const saveName = () => {
    if (name.trim() !== (asset.author_name ?? "")) save("name", name.trim() || null);
  };
  const onEnter = (e: ReactKeyboardEvent, fn: () => void) => {
    if (e.key === "Enter") {
      e.preventDefault();
      fn();
    }
  };
  const duration = formatDuration(asset.duration_s, t);
  const ld = asset.loudness;

  return (
    <aside className="lib-drawer" aria-label={t("library.card.title")}>
      <FontFaces assets={[asset]} />
      <button className="lib-close" onClick={onClose} aria-label={t("library.close")}>×</button>
      <h2 className="lib-drawer-ref">
        <code>{asset.ref}</code> <CopyRef value={asset.ref} />
      </h2>
      <div className="lib-large">
        <LargePreview asset={asset} />
      </div>
      <Badges asset={asset} />
      <dl className="lib-facts">
        <Field label={t("library.card.ref")}>
          <code>{`@${asset.category}/${asset.name}`}</code>
        </Field>
        {asset.aliases.length > 0 && (
          <Field label={t("library.card.aliases")}>
            {asset.aliases.map((a) => <code key={a} className="lib-alias">{a}</code>)}
          </Field>
        )}
        <Field label={t("library.card.category")}>
          {t(`library.category.${asset.category}` as "library.category.sfx")}
          {asset.category_source === "fallback" && <span className="muted"> · {t("library.card.fallback")}</span>}
        </Field>
        <Field label={t("library.card.folder")}>
          <code>{asset.folder}</code>
        </Field>
        {duration && <Field label={t("library.card.duration")}>{duration}</Field>}
        {asset.width && asset.height && <Field label={t("library.card.dimensions")}>{asset.width}×{asset.height}</Field>}
        {asset.fps && <Field label={t("library.card.fps")}>{asset.fps}</Field>}
        {asset.file.size !== null && <Field label={t("library.card.size")}>{formatSize(asset.file.size, t)}</Field>}
        {ld && (
          <Field label={t("library.card.loudness")}>
            {t("library.card.loudnessValue", {
              i: ld.i?.toFixed(1) ?? "—",
              tp: ld.tp?.toFixed(1) ?? "—",
              method: t(`library.loudness.${ld.method}`),
            })}
          </Field>
        )}
        <Field label={t("library.card.rights")}>
          <select
            value={asset.rights_override ?? ""}
            aria-label={t("library.card.rights")}
            onChange={(e) => save("rights", (e.target.value || null) as Rights | null)}
          >
            <option value="">{t("library.card.default", { rights: t(`library.rights.${asset.rights_default}`) })}</option>
            {(["own", "free", "unknown"] as const).map((r) => (
              <option key={r} value={r}>{t(`library.rights.${r}`)}</option>
            ))}
          </select>
          {errorFor("rights")}
        </Field>
      </dl>

      <section className="lib-author">
        <label>
          <span>{t("library.card.caption")}</span>
          <input value={caption} onChange={(e) => setCaption(e.target.value)} onBlur={saveCaption} onKeyDown={(e) => onEnter(e, saveCaption)} />
        </label>
        {errorFor("caption")}
        {asset.agent_caption && (
          <p className="lib-agent">
            {t("library.card.agent")}: {asset.agent_caption}{" "}
            {asset.agent_caption !== asset.caption && (
              <button className="link" onClick={() => save("caption", asset.agent_caption)}>{t("library.card.use")}</button>
            )}
          </p>
        )}
        <div className="lib-field">
          <span>{t("library.card.tags")}</span>
          <TagEditor tags={asset.tags} onChange={(tags) => save("tags", tags)} />
        </div>
        {errorFor("tags")}
        {asset.agent_tags.length > 0 && (
          <p className="lib-agent">
            {t("library.card.agent")}:{" "}
            {asset.agent_tags.map((tag) =>
              asset.tags.some((x) => x.toLowerCase() === tag.toLowerCase()) ? (
                <span key={tag} className="lib-chip muted">{tag}</span>
              ) : (
                <button key={tag} className="lib-chip adopt" title={t("library.card.adopt")} onClick={() => save("tags", [...asset.tags, tag])}>
                  + {tag}
                </button>
              ),
            )}
          </p>
        )}
        <label>
          <span>{t("library.card.name")}</span>
          <span className="lib-name">
            <code>@{asset.category}/</code>
            <input value={name} placeholder={asset.name} onChange={(e) => setName(e.target.value)} onBlur={saveName} onKeyDown={(e) => onEnter(e, saveName)} />
          </span>
        </label>
        {errorFor("name")}
      </section>

      {asset.variants && asset.variants.length > 0 && (
        <section>
          <h3>{t("library.card.variants")}</h3>
          <ul className="lib-variants">
            {asset.variants.map((v) => (
              <li key={v.path}>
                <span className="lib-badge">{t(`library.role.${v.role}`)}</span>{" "}
                {v.media ? <a href={mediaUrl(v.media)} target="_blank" rel="noreferrer">{v.path}</a> : <code>{v.path}</code>}
              </li>
            ))}
          </ul>
        </section>
      )}
      <p>
        <button onClick={() => onReveal(asset)}>{t("library.card.showInFinder")}</button>
      </p>
    </aside>
  );
}
