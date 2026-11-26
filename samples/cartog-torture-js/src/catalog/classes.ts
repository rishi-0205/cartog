/** OOP catalog — abstract, static, getter/setter, recursion. */
export abstract class A { abstract run(): void; }
export class B extends A {
  static make(): B { return new B(); }
  get ok(): boolean { return true; }
  set ok(v: boolean) { void v; }
  run(): void { super.run(); }
}
export function rec(n: number): number { return n > 0 ? rec(n - 1) : 0; }
