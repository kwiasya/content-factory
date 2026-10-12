import { CardPage } from "./CardPage";
import { ContourHome } from "./ContourHome";
import { IdeasPage } from "./IdeasPage";
import { CONTOUR_PREFIX, parseContour } from "./routes";
import { SummariesPage } from "./SummariesPage";
import { TaxonomyPage } from "./TaxonomyPage";
import { WatchlistPage } from "./WatchlistPage";
import "./contour.css";

export function ContourNav({ hash }: { hash: string }) {
  return (
    <a href={CONTOUR_PREFIX} className={parseContour(hash) ? "nav active" : "nav"}>
      Contour
    </a>
  );
}

export function contourRoute(hash: string) {
  const view = parseContour(hash);
  if (view === null) {
    return null;
  }
  switch (view.page) {
    case "watchlist":
      return <WatchlistPage key={view.name} name={view.name} />;
    case "summary":
      return <SummariesPage key={view.name} name={view.name} />;
    case "card":
      return <CardPage key={view.id} id={view.id} />;
    case "ideas":
      return <IdeasPage selected={view.id} />;
    case "taxonomy":
      return <TaxonomyPage />;
    default:
      return <ContourHome />;
  }
}
