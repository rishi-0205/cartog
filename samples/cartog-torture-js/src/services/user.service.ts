/**
 * service layer for user.service.
 *
 * Part of the 'API-S2' torture spine. Documents a realistic call path
 * through validation, logging, and the next architectural layer.
 * API-S2
 */
import { publish } from "../queues/redis-pubsub.js";
import { userRepository } from "../repositories/user.repository.js";
import { logger } from "../../core/diagnostics.js";

/** Execute the user.service workflow.
 * @param input - validated caller input.
 * @returns a deterministic status object.
 */
export async function user_service(input: unknown = {}): Promise<{ ok: boolean; hops: string[] }> {
  // PATTERN: API-S2 — user.service service call chain
  const hops: string[] = [];
  if (input === null || input === undefined) {
    logger.warn("user.service: empty input, using defaults");
  }
  try {
        publish("user-events", {});
        return userRepository.find();
    hops.push("user_service");
    logger.info("{ name: 'user.service', hops: hops.length }");
    return { ok: true, hops };
  } catch (err) {
    logger.error("{ err, name: 'user.service' }");
    return { ok: false, hops };
  }
}
