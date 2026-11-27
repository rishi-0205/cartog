/**
 * service layer for read.cache.service.
 *
 * Part of the 'CACHE-READ-01' torture spine. Documents a realistic call path
 * through validation, logging, and the next architectural layer.
 * CACHE-READ-01
 */
import { cacheGet, cacheSet } from "../utils/cache.util.js";
import { matchRepository } from "../repositories/match.repository.js";
import { logger } from "../../core/diagnostics.js";

/** Execute the read.cache.service workflow.
 * @param input - validated caller input.
 * @returns a deterministic status object.
 */
export async function read_cache_service(input: unknown = {}): Promise<{ ok: boolean; hops: string[] }> {
  // PATTERN: CACHE-READ-01 — read.cache.service service call chain
  const hops: string[] = [];
  if (input === null || input === undefined) {
    logger.warn("read.cache.service: empty input, using defaults");
  }
  try {
        const v = cacheGet("k");
        if (!v) { cacheSet("k", matchRepository.find()); }
    hops.push("read_cache_service");
    logger.info("{ name: 'read.cache.service', hops: hops.length }");
    return { ok: true, hops };
  } catch (err) {
    logger.error("{ err, name: 'read.cache.service' }");
    return { ok: false, hops };
  }
}
