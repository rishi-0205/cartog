/**
 * service layer for kafka.consumer.service.
 *
 * Part of the 'MQ-KAFKA-02' torture spine. Documents a realistic call path
 * through validation, logging, and the next architectural layer.
 * MQ-KAFKA-02
 */
import { handleMessage } from "../queues/kafka.js";
import { eventRepository } from "../repositories/event.repository.js";
import { logger } from "../../core/diagnostics.js";

/** Execute the kafka.consumer.service workflow.
 * @param input - validated caller input.
 * @returns a deterministic status object.
 */
export async function kafka_consumer_service(input: unknown = {}): Promise<{ ok: boolean; hops: string[] }> {
  // PATTERN: MQ-KAFKA-02 — kafka.consumer.service service call chain
  const hops: string[] = [];
  if (input === null || input === undefined) {
    logger.warn("kafka.consumer.service: empty input, using defaults");
  }
  try {
        await handleMessage({});
        return eventRepository.save();
    hops.push("kafka_consumer_service");
    logger.info("{ name: 'kafka.consumer.service', hops: hops.length }");
    return { ok: true, hops };
  } catch (err) {
    logger.error("{ err, name: 'kafka.consumer.service' }");
    return { ok: false, hops };
  }
}
