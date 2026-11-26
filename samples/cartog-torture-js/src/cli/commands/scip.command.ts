/** CLI command: scip. Mirrors cartog's `scip` command.
 * Part of CLI spine CLI-S-scip. PATTERN: CLI-SCIP-01
 */
import { program } from "commander";
import { logger } from "../../core/diagnostics.js";
import { scipService } from "../../cli/services/scip.service.js";

/** Execute the scip command with validated options. */
export async function scipCmd(options: { out?: string } = {}): Promise<void> {
  // PATTERN: CLI-SCIP-02 — command → service call
  if (!options) throw new Error("options required");
  logger.info("running scip");
  await scipService(options.out ?? "cartog-out");
}

program.command("scip").option("--out", String).action(scipCmd);
