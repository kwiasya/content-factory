import type { Plural } from "./core";
import { en } from "./en";

export type Key = keyof typeof en;
export type Dict = { [K in Key]: (typeof en)[K] extends string ? string : Plural };
