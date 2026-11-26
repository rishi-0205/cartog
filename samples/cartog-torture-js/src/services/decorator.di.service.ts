/**
 * service layer for decorator.di.service.
 *
 * Part of the 'DI-DECORATOR-01' torture spine. Documents a realistic call path
 * through validation, logging, and the next architectural layer.
 * DI-DECORATOR-01
 */
import { Service } from "../di/decorators.js";
import { logger } from "../../core/diagnostics.js";

/** Execute the decorator.di.service workflow.
 * @param input - validated caller input.
 * @returns a deterministic status object.
 */
export async function decorator.di.service(input: unknown = {}): Promise<{ ok: boolean; hops: string[] }> {
  // PATTERN: DI-DECORATOR-01 — decorator.di.service service call chain
  const hops: string[] = [];
  if (input === null || input === undefined) {
    logger.warn("decorator.di.service: empty input, using defaults");
  }
  try {
        return new Service().run();
    hops.push("decorator.di.service");
    logger.info("{ name: 'decorator.di.service', hops: hops.length }");
    return { ok: true, hops };
  } catch (err) {
    logger.error("{ err, name: 'decorator.di.service' }");
    return { ok: false, hops };
  }
}
