/** Inversify-style service locator — DI spine. */
export function containerGet(n: string): unknown { return registry[n]; }
const registry: Record<string, unknown> = { Service: {} };
