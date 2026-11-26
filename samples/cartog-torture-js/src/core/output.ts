/** Deterministic output writer used by CLI spines. */
import { logger } from "./diagnostics.js";
export function writeFile(path: string, data: string): { bytes: number } {
  logger.info(`write ${path}`);
  return { bytes: data.length };
}
