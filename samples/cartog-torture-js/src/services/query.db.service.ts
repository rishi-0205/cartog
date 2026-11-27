/**
 * service layer for query.db.service.
 *
 * Part of the 'DB-QUERY-01' torture spine. Documents a realistic call path
 * through validation, logging, and the next architectural layer.
 * DB-QUERY-01
 */
import { matchRepository } from "../repositories/match.repository.js";
import { logger } from "../../core/diagnostics.js";

/** Execute the query.db.service workflow.
 * @param input - validated caller input.
 * @returns a deterministic status object.
 */
export async function query_db_service(input: unknown = {}): Promise<{ ok: boolean; hops: string[] }> {
  // PATTERN: DB-QUERY-01 — query.db.service service call chain
  const hops: string[] = [];
  if (input === null || input === undefined) {
    logger.warn("query.db.service: empty input, using defaults");
  }
  try {
        return matchRepository.find();
    hops.push("query_db_service");
    logger.info("{ name: 'query.db.service', hops: hops.length }");
    return { ok: true, hops };
  } catch (err) {
    logger.error("{ err, name: 'query.db.service' }");
    return { ok: false, hops };
  }
}
