import { platformName, platformShort, type Platform } from "./api";

export function PlatformBadge({
  platform,
  count,
}: {
  platform: Platform | undefined;
  count?: number;
}) {
  const p = platform ?? "youtube";
  return (
    <span className={`badge platform platform-${p}`} title={platformName(p)}>
      {platformShort(p)}
      {count !== undefined ? ` ${count}` : ""}
    </span>
  );
}
