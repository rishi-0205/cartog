// PATTERN: DYN-COMPUTED-01 — computed dynamic keys (abstain)
const key = "m";
const o: Record<string, () => void> = { [key + "x"]: () => {}, [key](): void { return; } };
o[key]();
