/** Alias chain consumer. */
import { renamed } from "./alias-b.js";
export function aliasConsumer(x: unknown): unknown { return renamed(x); }
