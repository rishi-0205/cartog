// PATTERN: EVENT-DYNAMIC-01 — dynamic event name (abstain)
const key = process.env.EVENT || "e";
e.emit(key, {});
const e2 = { emit(): void { return; } };
declare const e: { emit(n: string, d: unknown): void };
