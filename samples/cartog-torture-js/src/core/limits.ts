// PATTERN: REF-ISINSTANCE-01 — isinstance-style type check reference
export function classify(x: unknown): void { if (typeof x === "string") return; }
