// PATTERN: CALL-DYNAMIC-IMPORT-01 — dynamic import(var) (abstain)
export async function load(name: string): Promise<void> { await import(name); }
