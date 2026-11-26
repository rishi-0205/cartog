/** In-memory cache utility — cache spines. */
const store = new Map<string, unknown>();
export function cacheGet(k: string): unknown { return store.get(k); }
export function cacheSet(k: string, v: unknown): void { store.set(k, v); }
export function cacheDel(k: string): void { store.delete(k); }
export function cacheExpire(k: string, ttl: number): void { setTimeout(() => store.delete(k), ttl * 1000); }
