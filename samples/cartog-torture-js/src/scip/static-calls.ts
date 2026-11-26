// PATTERN: CALL-PARTIAL-01 — bound/partial-style call
export function mk(): void { const f = decode.bind(null); f(); }
async function decode(): Promise<void> { return; }
