/**
 * service layer for admin.service.
 *
 * Part of the 'API-S5' torture spine. Documents a realistic call path
 * through validation, logging, and the next architectural layer.
 * API-S5
 */
import { sendKafka } from "../queues/kafka.js";
import { adminRepository } from "../repositories/admin.repository.js";
import { logger } from "../../core/diagnostics.js";

/** Execute the admin.service workflow.
 * @param input - validated caller input.
 * @returns a deterministic status object.
 */
export async function admin.service(input: unknown = {}): Promise<{ ok: boolean; hops: string[] }> {
  // PATTERN: API-S5 — admin.service service call chain
  const hops: string[] = [];
  if (input === null || input === undefined) {
    logger.warn("admin.service: empty input, using defaults");
  }
  try {
        await sendKafka("events", {});
        return adminRepository.rebuild();
    hops.push("admin.service");
    logger.info("{ name: 'admin.service', hops: hops.length }");
    return { ok: true, hops };
  } catch (err) {
    logger.error("{ err, name: 'admin.service' }");
    return { ok: false, hops };
  }
}
