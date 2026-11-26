/** Dynamic composition catalog — all must abstain. */
const target: Record<string, unknown> = {};
Object.assign(target, { method(): void { return; } });
const computed = { a: 1 };
const spread = { ...computed };
const key = "m";
const o: Record<string, () => void> = { [key + "x"]: () => {} };
o[key]();
const p = new Proxy({}, { get: () => () => {} });
Reflect.get(p, "x");
void spread;
