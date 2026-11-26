/** CLI command: flow. Mirrors cartog's `flow` command.
 * Part of CLI spine CLI-S-flow. PATTERN: CLI-FLOW-01
 */
import { program } from "commander";
import { logger } from "../../core/diagnostics.js";
import { flowService } from "../../cli/services/flow.service.js";

/** Execute the flow command with validated options. */
export async function flowCmd(options: { out?: string } = {}): Promise<void> {
  // PATTERN: CLI-FLOW-02 — command → service call
  if (!options) throw new Error("options required");
  logger.info("running flow");
  await flowService(options.out ?? "cartog-out");
}

program.command("flow").option("--out", String).action(flowCmd);
