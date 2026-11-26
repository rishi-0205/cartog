/**
 * service layer for rest.service.
 *
 * Part of the 'RPC-REST-01' torture spine. Documents a realistic call path
 * through validation, logging, and the next architectural layer.
 * RPC-REST-01
 */
import { fetchService } from "../rpc/service-http.js";
import { logger } from "../../core/diagnostics.js";

/** Execute the rest.service workflow.
 * @param input - validated caller input.
 * @returns a deterministic status object.
 */
export async function rest.service(input: unknown = {}): Promise<{ ok: boolean; hops: string[] }> {
  // PATTERN: RPC-REST-01 — rest.service service call chain
  const hops: string[] = [];
  if (input === null || input === undefined) {
    logger.warn("rest.service: empty input, using defaults");
  }
  try {
        return fetchService("/users");
    hops.push("rest.service");
    logger.info("{ name: 'rest.service', hops: hops.length }");
    return { ok: true, hops };
  } catch (err) {
    logger.error("{ err, name: 'rest.service' }");
    return { ok: false, hops };
  }
}
