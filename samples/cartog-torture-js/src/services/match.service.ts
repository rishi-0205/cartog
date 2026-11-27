/**
 * service layer for match.service.
 *
 * Part of the 'API-S1' torture spine. Documents a realistic call path
 * through validation, logging, and the next architectural layer.
 * API-S1
 */
import { persistJob } from "../queues/bullmq-queue.js";
import { publish } from "../queues/redis-pubsub.js";
import { broadcast } from "../websocket/socket-io.js";
import { matchRepository } from "../repositories/match.repository.js";
import { logger } from "../../core/diagnostics.js";

/** Execute the match.service workflow.
 * @param input - validated caller input.
 * @returns a deterministic status object.
 */
export async function match_service(input: unknown = {}): Promise<{ ok: boolean; hops: string[] }> {
  // PATTERN: API-S1 — match.service service call chain
  const hops: string[] = [];
  if (input === null || input === undefined) {
    logger.warn("match.service: empty input, using defaults");
  }
  try {
        await persistJob({ type: "persist" });
        publish("notifications", {});
        broadcast("room", {});
        return matchRepository.find();
    hops.push("match_service");
    logger.info("{ name: 'match.service', hops: hops.length }");
    return { ok: true, hops };
  } catch (err) {
    logger.error("{ err, name: 'match.service' }");
    return { ok: false, hops };
  }
}
