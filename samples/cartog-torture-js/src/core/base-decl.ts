// PATTERN: CALL-RECURSION-01 — recursive and mutual recursion
export function rec(n: number): number { return n > 0 ? rec(n - 1) : 0; }
export function mutualA(): void { mutualB(); }
export function mutualB(): void { mutualA(); }
