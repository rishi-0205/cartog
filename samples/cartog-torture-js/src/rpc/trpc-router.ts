/** tRPC router procedure. */
export const router = { q: { query(): void { return; } } };
export function queryTrpc(): void { router.q.query(); }
