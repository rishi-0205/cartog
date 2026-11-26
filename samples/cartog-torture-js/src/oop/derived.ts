// PATTERN: OOP-OVERRIDE-01 — super.method override edge
import { Shape } from "./base.js";
export class Circle extends Shape { area(): number { return super.area(); } }
