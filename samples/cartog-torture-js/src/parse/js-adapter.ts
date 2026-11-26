// PATTERN: CALL-CHAIN-REEXPORT-01 — A.B.C() through import alias
import { JSAdapter as A } from "./base.js";
export function resolve(): void { A.prototype.parse(); }
