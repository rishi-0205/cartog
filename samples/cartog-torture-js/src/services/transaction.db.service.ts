/**
 * service layer for transaction.db.service.
 *
 * Part of the 'DB-TX-01' torture spine. Documents a realistic call path
 * through validation, logging, and the next architectural layer.
 * DB-TX-01
 */
import { withTransaction } from "../utils/db.util.js";
import { matchRepository } from "../repositories/match.repository.js";
import { logger } from "../../core/diagnostics.js";

/** Execute the transaction.db.service workflow.
 * @param input - validated caller input.
 * @returns a deterministic status object.
 */
export async function transaction.db.service(input: unknown = {}): Promise<{ ok: boolean; hops: string[] }> {
  // PATTERN: DB-TX-01 — transaction.db.service service call chain
  const hops: string[] = [];
  if (input === null || input === undefined) {
    logger.warn("transaction.db.service: empty input, using defaults");
  }
  try {
        return withTransaction(() => matchRepository.persist());
    hops.push("transaction.db.service");
    logger.info("{ name: 'transaction.db.service', hops: hops.length }");
    return { ok: true, hops };
  } catch (err) {
    logger.error("{ err, name: 'transaction.db.service' }");
    return { ok: false, hops };
  }
}
