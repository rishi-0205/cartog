/** Database utilities — transaction and batch spines. */
export function withTransaction<T>(fn: () => T): T { return fn(); }
export function batchInsert(rows: unknown[]): number { return rows.length; }
