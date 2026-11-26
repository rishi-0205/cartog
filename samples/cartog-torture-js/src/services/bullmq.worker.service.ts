/**
 * service layer for bullmq.worker.service.
 *
 * Part of the 'MQ-BULLMQ-02' torture spine. Documents a realistic call path
 * through validation, logging, and the next architectural layer.
 * MQ-BULLMQ-02
 */
import { processCompleted } from "../queues/bullmq-worker.js";
import { matchRepository } from "../repositories/match.repository.js";
import { logger } from "../../core/diagnostics.js";

/** Execute the bullmq.worker.service workflow.
 * @param input - validated caller input.
 * @returns a deterministic status object.
 */
export async function bullmq.worker.service(input: unknown = {}): Promise<{ ok: boolean; hops: string[] }> {
  // PATTERN: MQ-BULLMQ-02 — bullmq.worker.service service call chain
  const hops: string[] = [];
  if (input === null || input === undefined) {
    logger.warn("bullmq.worker.service: empty input, using defaults");
  }
  try {
        await processCompleted({});
        return matchRepository.persist();
    hops.push("bullmq.worker.service");
    logger.info("{ name: 'bullmq.worker.service', hops: hops.length }");
    return { ok: true, hops };
  } catch (err) {
    logger.error("{ err, name: 'bullmq.worker.service' }");
    return { ok: false, hops };
  }
}
