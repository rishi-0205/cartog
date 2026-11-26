/**
 * cli service layer for check.
 *
 * Part of the 'CLI-S-CHECK-01' torture spine. Documents a realistic call path
 * through validation, logging, and the next architectural layer.
 * CLI-S-CHECK-01
 */
import { validateGraph } from "../../graph/validate.js";
import { logger } from "../../core/diagnostics.js";
import { logger } from "../../core/diagnostics.js";

/** Execute the check workflow.
 * @param input - validated caller input.
 * @returns a deterministic status object.
 */
export async function check(input: unknown = {}): Promise<{ ok: boolean; hops: string[] }> {
  // PATTERN: CLI-S-CHECK-01 — check cli service call chain
  const hops: string[] = [];
  if (input === null || input === undefined) {
    logger.warn("check: empty input, using defaults");
  }
  try {
        const r = validateGraph(null as never);
        logger.info(`errors=${r.length}`);
    hops.push("check");
    logger.info("{ name: 'check', hops: hops.length }");
    return { ok: true, hops };
  } catch (err) {
    logger.error("{ err, name: 'check' }");
    return { ok: false, hops };
  }
}
