import { useEffect, useState } from "react";
import { api } from "./api";

/** Who runs this Desk (`CF_PERSON`), from `/api/meta`; `name` stays null while loading or when meta failed. */
export interface Person {
  state: "loading" | "known" | "unknown";
  name: string | null;
}

export function usePerson(): Person {
  const [person, setPerson] = useState<Person>({ state: "loading", name: null });
  useEffect(() => {
    api.meta().then(
      (m) => setPerson({ state: "known", name: m.person }),
      () => setPerson({ state: "unknown", name: null }),
    );
  }, []);
  return person;
}

/** True only when the row surely belongs to another person; an empty owner or an unknown person is never foreign. */
export function isForeign(owner: string | null | undefined, person: Person): boolean {
  return person.state === "known" && !!owner && owner !== person.name;
}
