/** Core graph model — class, method, override, and new-expression patterns. */
export class Base {
  /** Base operation overridden by subclasses. */
  make(): string { return "base"; }
}
export class Node extends Base {
  /** Override that calls super — emits an overrides edge. */
  make(): string { return super.make() + ":node"; }
}
// PATTERN: CALL-NEW-01 — new X() constructor (references, not calls)
export const node = new Node();
