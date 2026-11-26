/** SCIP indexer runner used by the analyze spine. */
import { buildGraph } from "../graph/merge.js";
export async function indexProject(out: string): Promise<void> {
  // PATTERN: CALL-ASYNC-01 — async/await chain
  await decode();
  buildGraph([]);
  console.log(out);
}
async function decode(): Promise<void> { return; }
