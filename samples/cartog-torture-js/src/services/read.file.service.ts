/**
 * service layer for read.file.service.
 *
 * Part of the 'FILE-READ-01' torture spine. Documents a realistic call path
 * through validation, logging, and the next architectural layer.
 * FILE-READ-01
 */
import { readConfig } from "../utils/file.util.js";
import { logger } from "../../core/diagnostics.js";

/** Execute the read.file.service workflow.
 * @param input - validated caller input.
 * @returns a deterministic status object.
 */
export async function read.file.service(input: unknown = {}): Promise<{ ok: boolean; hops: string[] }> {
  // PATTERN: FILE-READ-01 — read.file.service service call chain
  const hops: string[] = [];
  if (input === null || input === undefined) {
    logger.warn("read.file.service: empty input, using defaults");
  }
  try {
        return readConfig("config.json");
    hops.push("read.file.service");
    logger.info("{ name: 'read.file.service', hops: hops.length }");
    return { ok: true, hops };
  } catch (err) {
    logger.error("{ err, name: 'read.file.service' }");
    return { ok: false, hops };
  }
}
