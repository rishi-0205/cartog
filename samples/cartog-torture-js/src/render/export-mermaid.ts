/** Mermaid exporter used by flow/map spines. */
import { traceCallFlow } from "./views.js";
export function exportMermaid(g: unknown): string {
  traceCallFlow(g);
  return "graph TD";
}
