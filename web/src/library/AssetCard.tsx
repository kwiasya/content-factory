import { useState } from "react";
import { mediaUrl } from "../api";
import { useT, type T } from "../i18n";
import { FontSample } from "./FontSample";
import type { AssetCard as Card } from "./libraryApi";
import { toggle, usePlaying } from "./player";

export function formatDuration(s: number | null, t: T): string | null {
  if (s === null || s === undefined) {
    return null;
  }
  return t("unit.s", { n: Math.round(s * 10) / 10 });
}

export function Badges({ asset }: { asset: Card }) {
  const t = useT();
  return (
    <span className="lib-badges">
      {asset.alpha && <span className="lib-badge">{t("library.badge.alpha")}</span>}
      {asset.green_screen && <span className="lib-badge green">{t("library.badge.green")}</span>}
      <span className={`lib-badge rights-${asset.rights}`}>{t(`library.rights.${asset.rights}`)}</span>
      {asset.loudness?.i !== null && asset.loudness?.i !== undefined && (
        <span className="lib-badge" title={t("library.card.loudness")}>
          {t("library.badge.loudness", { i: asset.loudness.i.toFixed(1) })}
        </span>
      )}
    </span>
  );
}

export function PlayButton({ asset }: { asset: Card }) {
  const t = useT();
  const playing = usePlaying() === asset.id;
  if (!asset.media.original) {
    return null;
  }
  return (
    <button
      className={playing ? "lib-play playing" : "lib-play"}
      aria-pressed={playing}
      aria-label={t(playing ? "library.stop" : "library.play")}
      onClick={(e) => {
        e.stopPropagation();
        toggle(asset.id, asset.media.original!);
      }}
    >
      {playing ? "■" : "▶"}
    </button>
  );
}

function Visual({ asset }: { asset: Card }) {
  const t = useT();
  const [hover, setHover] = useState(false);
  if (asset.kind === "audio") {
    return (
      <div className="lib-visual audio">
        <PlayButton asset={asset} />
      </div>
    );
  }
  if (asset.kind === "font") {
    return (
      <div className="lib-visual font">
        <FontSample asset={asset} />
      </div>
    );
  }
  if (asset.kind === "template") {
    return (
      <div className="lib-visual template">
        <span>{asset.file.name}</span>
      </div>
    );
  }
  const poster = asset.media.poster ?? asset.media.png ?? (asset.kind === "image" ? asset.media.original : null);
  return (
    <div
      className="lib-visual"
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
    >
      {hover && asset.kind === "video" && asset.media.preview ? (
        <video src={mediaUrl(asset.media.preview)} muted loop autoPlay playsInline preload="none" />
      ) : poster ? (
        <img src={mediaUrl(poster)} alt={asset.ref} loading="lazy" />
      ) : (
        <span className="muted">{t("library.noPreview")}</span>
      )}
    </div>
  );
}

export function AssetTile({ asset, selected, onOpen, onReveal }: {
  asset: Card;
  selected: boolean;
  onOpen: () => void;
  onReveal: () => void;
}) {
  const t = useT();
  const duration = asset.kind === "video" || asset.kind === "audio" ? formatDuration(asset.duration_s, t) : null;
  return (
    <li className={selected ? "lib-tile selected" : "lib-tile"}>
      <div className="lib-open" onClick={onOpen}>
        <Visual asset={asset} />
      </div>
      <div className="lib-tile-meta">
        <button className="lib-ref link" onClick={onOpen} title={asset.caption ?? asset.agent_caption ?? asset.ref}>
          {asset.ref}
        </button>
        {duration && <span className="muted">{duration}</span>}
      </div>
      <Badges asset={asset} />
      {asset.kind === "template" && (
        <button className="lib-reveal" onClick={onReveal}>
          {t("library.card.showInFinder")}
        </button>
      )}
    </li>
  );
}
