// PATTERN: DYN-PROXY-01 — Proxy / Reflect (abstain)
const p = new Proxy({}, { get: () => () => {} });
Reflect.get(p, "x");
