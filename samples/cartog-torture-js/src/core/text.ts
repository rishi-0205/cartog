// PATTERN: CALL-CALLBACK-01 — callback passed as arg
export function withCb(cb: () => void): void { cb(); }
