/** Import/export catalog — barrels, type-only, circular, dynamic. */
export * from "./classes.js";
export { A as Renamed } from "./classes.js";
import type { B } from "./classes.js";
export async function load(n: string): Promise<void> { await import(n); require(n); }
