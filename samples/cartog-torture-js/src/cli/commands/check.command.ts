/** CLI command: check. Mirrors cartog's `check` command.
 * Part of CLI spine CLI-S-check. PATTERN: CLI-CHECK-01
 */
import { program } from "commander";
import { logger } from "../../core/diagnostics.js";
import { checkService } from "../../cli/services/check.service.js";

/** Execute the check command with validated options. */
export async function checkCmd(options: { out?: string } = {}): Promise<void> {
  // PATTERN: CLI-CHECK-02 — command → service call
  if (!options) throw new Error("options required");
  logger.info("running check");
  await checkService(options.out ?? "cartog-out");
}

program.command("check").option("--out", String).action(checkCmd);
