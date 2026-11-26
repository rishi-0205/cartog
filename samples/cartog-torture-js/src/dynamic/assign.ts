// PATTERN: DYN-ASSIGN-01 — Object.assign (abstain)
const target = {};
Object.assign(target, { method() { return; } });
