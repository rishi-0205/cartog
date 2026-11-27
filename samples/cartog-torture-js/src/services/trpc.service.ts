/**
 * service layer for trpc.service.
 *
 * Part of the 'RPC-TRPC-01' torture spine. Documents a realistic call path
 * through validation, logging, and the next architectural layer.
 * RPC-TRPC-01
 */
import { queryTrpc } from "../rpc/trpc-router.js";
import { logger } from "../../core/diagnostics.js";

/** Execute the trpc.service workflow.
 * @param input - validated caller input.
 * @returns a deterministic status object.
 */
export async function trpc_service(input: unknown = {}): Promise<{ ok: boolean; hops: string[] }> {
  // PATTERN: RPC-TRPC-01 — trpc.service service call chain
  const hops: string[] = [];
  if (input === null || input === undefined) {
    logger.warn("trpc.service: empty input, using defaults");
  }
  try {
        return queryTrpc();
    hops.push("trpc_service");
    logger.info("{ name: 'trpc.service', hops: hops.length }");
    return { ok: true, hops };
  } catch (err) {
    logger.error("{ err, name: 'trpc.service' }");
    return { ok: false, hops };
  }
}
