// PATTERN: REF-CALLBACK-01 — callback reference
export function exportJson(cb: () => void): void { cb(); }
