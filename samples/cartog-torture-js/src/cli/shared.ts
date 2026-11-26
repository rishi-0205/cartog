// PATTERN: CALL-DOTTED-01 — dotted chain A.B.C() via import
import { Graph } from "../graph/merge.js";
export function shared(): void { Graph.build().validate(); }
