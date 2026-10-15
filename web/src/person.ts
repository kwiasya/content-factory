import { useEffect, useState } from "react";
import { api } from "./api";

export function usePerson(): string | null {
  const [person, setPerson] = useState<string | null>(null);
  useEffect(() => {
    api.meta().then(
      (m) => setPerson(m.person),
      () => setPerson(null),
    );
  }, []);
  return person;
}

export function isMine(owner: string | null | undefined, person: string | null): boolean {
  return !owner || owner === person;
}
