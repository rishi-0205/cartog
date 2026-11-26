/**
 * service layer for cron.job.service.
 *
 * Part of the 'SCHED-CRON-01' torture spine. Documents a realistic call path
 * through validation, logging, and the next architectural layer.
 * SCHED-CRON-01
 */
import { matchRepository } from "../repositories/match.repository.js";
import { logger } from "../../core/diagnostics.js";

/** Execute the cron.job.service workflow.
 * @param input - validated caller input.
 * @returns a deterministic status object.
 */
export async function cron.job.service(input: unknown = {}): Promise<{ ok: boolean; hops: string[] }> {
  // PATTERN: SCHED-CRON-01 — cron.job.service service call chain
  const hops: string[] = [];
  if (input === null || input === undefined) {
    logger.warn("cron.job.service: empty input, using defaults");
  }
  try {
        return matchRepository.rebuild();
    hops.push("cron.job.service");
    logger.info("{ name: 'cron.job.service', hops: hops.length }");
    return { ok: true, hops };
  } catch (err) {
    logger.error("{ err, name: 'cron.job.service' }");
    return { ok: false, hops };
  }
}
