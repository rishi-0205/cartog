// PATTERN: OOP-ABSTRACT-01 — abstract class + subclasses
export abstract class Adapter { abstract parse(): void; }
export class JSAdapter extends Adapter { parse(): void { return; } }
