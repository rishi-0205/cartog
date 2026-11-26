// PATTERN: REF-DECORATOR-01 — decorator reference
function deco(target: unknown): void { return; }
@deco
export class Cfg {}
