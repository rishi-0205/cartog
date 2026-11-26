// PATTERN: PLUGIN-DYNAMIC-REQUIRE-01 — require(variable) (abstain)
export function load(name: string): void { require(name); }
