/**
 * service layer for grpc.client.service.
 *
 * Part of the 'RPC-GRPC-01' torture spine. Documents a realistic call path
 * through validation, logging, and the next architectural layer.
 * RPC-GRPC-01
 */
import { callGrpc } from "../rpc/grpc-client.js";
import { userRepository } from "../repositories/user.repository.js";
import { logger } from "../../core/diagnostics.js";

/** Execute the grpc.client.service workflow.
 * @param input - validated caller input.
 * @returns a deterministic status object.
 */
export async function grpc_client_service(input: unknown = {}): Promise<{ ok: boolean; hops: string[] }> {
  // PATTERN: RPC-GRPC-01 — grpc.client.service service call chain
  const hops: string[] = [];
  if (input === null || input === undefined) {
    logger.warn("grpc.client.service: empty input, using defaults");
  }
  try {
        await callGrpc();
        return userRepository.find();
    hops.push("grpc_client_service");
    logger.info("{ name: 'grpc.client.service', hops: hops.length }");
    return { ok: true, hops };
  } catch (err) {
    logger.error("{ err, name: 'grpc.client.service' }");
    return { ok: false, hops };
  }
}
