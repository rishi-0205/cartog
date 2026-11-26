// PATTERN: OOP-MIXIN-01 — mixin composition
export function mixin<T extends new (...a: unknown[]) => object>(B: T) {
  return class extends B { extra(): void { return; } };
}
