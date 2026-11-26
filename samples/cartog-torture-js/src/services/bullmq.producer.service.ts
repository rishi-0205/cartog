/**
 * service layer for bullmq.producer.service.
 *
 * Part of the 'MQ-BULLMQ-01' torture spine. Documents a realistic call path
 * through validation, logging, and the next architectural layer.
 * MQ-BULLMQ-01
 */
import { addJob, addBulkJobs } from "../queues/bullmq-queue.js";
import { logger } from "../../core/diagnostics.js";

/** Execute the bullmq.producer.service workflow.
 * @param input - validated caller input.
 * @returns a deterministic status object.
 */
export async function bullmq.producer.service(input: unknown = {}): Promise<{ ok: boolean; hops: string[] }> {
  // PATTERN: MQ-BULLMQ-01 — bullmq.producer.service service call chain
  const hops: string[] = [];
  if (input === null || input === undefined) {
    logger.warn("bullmq.producer.service: empty input, using defaults");
  }
  try {
        await addJob("persist", {});
        await addBulkJobs([{ name: "x", data: {} }]);
    hops.push("bullmq.producer.service");
    logger.info("{ name: 'bullmq.producer.service', hops: hops.length }");
    return { ok: true, hops };
  } catch (err) {
    logger.error("{ err, name: 'bullmq.producer.service' }");
    return { ok: false, hops };
  }
}
