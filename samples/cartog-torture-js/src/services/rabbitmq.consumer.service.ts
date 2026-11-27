/**
 * service layer for rabbitmq.consumer.service.
 *
 * Part of the 'MQ-RABBITMQ-02' torture spine. Documents a realistic call path
 * through validation, logging, and the next architectural layer.
 * MQ-RABBITMQ-02
 */
import { onMessage } from "../queues/rabbitmq.js";
import { matchRepository } from "../repositories/match.repository.js";
import { logger } from "../../core/diagnostics.js";

/** Execute the rabbitmq.consumer.service workflow.
 * @param input - validated caller input.
 * @returns a deterministic status object.
 */
export async function rabbitmq_consumer_service(input: unknown = {}): Promise<{ ok: boolean; hops: string[] }> {
  // PATTERN: MQ-RABBITMQ-02 — rabbitmq.consumer.service service call chain
  const hops: string[] = [];
  if (input === null || input === undefined) {
    logger.warn("rabbitmq.consumer.service: empty input, using defaults");
  }
  try {
        onMessage({}, {}, {}, "body");
        return matchRepository.persist();
    hops.push("rabbitmq_consumer_service");
    logger.info("{ name: 'rabbitmq.consumer.service', hops: hops.length }");
    return { ok: true, hops };
  } catch (err) {
    logger.error("{ err, name: 'rabbitmq.consumer.service' }");
    return { ok: false, hops };
  }
}
