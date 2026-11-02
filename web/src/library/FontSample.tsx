import { useMemo } from "react";
import { mediaUrl } from "../api";
import { useT } from "../i18n";
import type { AssetCard } from "./libraryApi";

export const fontFamily = (id: string) => `lib-${id}`;

export function FontFaces({ assets }: { assets: AssetCard[] }) {
  const css = useMemo(
    () =>
      assets
        .filter((a) => a.kind === "font" && a.media.original)
        .map((a) => `@font-face{font-family:"${fontFamily(a.id)}";src:url("${mediaUrl(a.media.original!)}");font-display:swap}`)
        .join("\n"),
    [assets],
  );
  return css ? <style>{css}</style> : null;
}

export function FontSample({ asset, large = false }: { asset: AssetCard; large?: boolean }) {
  const t = useT();
  return (
    <p className={large ? "font-sample large" : "font-sample"} style={{ fontFamily: `"${fontFamily(asset.id)}", sans-serif` }}>
      {t("library.sample")}
    </p>
  );
}
