/**
 * cli service layer for doctor.
 *
 * Part of the 'CLI-S-DOCTOR-01' torture spine. Documents a realistic call path
 * through validation, logging, and the next architectural layer.
 * CLI-S-DOCTOR-01
 */
import { checkToolchain } from "../../core/toolchain.js";
import { logger } from "../../core/diagnostics.js";
import { logger } from "../../core/diagnostics.js";

/** Execute the doctor workflow.
 * @param input - validated caller input.
 * @returns a deterministic status object.
 */
export async function doctor(input: unknown = {}): Promise<{ ok: boolean; hops: string[] }> {
  // PATTERN: CLI-S-DOCTOR-01 — doctor cli service call chain
  const hops: string[] = [];
  if (input === null || input === undefined) {
    logger.warn("doctor: empty input, using defaults");
  }
  try {
        const ok = checkToolchain();
        logger.info(`toolchain=${ok}`);
    hops.push("doctor");
    logger.info("{ name: 'doctor', hops: hops.length }");
    return { ok: true, hops };
  } catch (err) {
    logger.error("{ err, name: 'doctor' }");
    return { ok: false, hops };
  }
}
