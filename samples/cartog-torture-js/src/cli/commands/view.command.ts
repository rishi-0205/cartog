/** CLI command: view. Mirrors cartog's `view` command.
 * Part of CLI spine CLI-S-view. PATTERN: CLI-VIEW-01
 */
import { program } from "commander";
import { logger } from "../../core/diagnostics.js";
import { viewService } from "../../cli/services/view.service.js";

/** Execute the view command with validated options. */
export async function viewCmd(options: { out?: string } = {}): Promise<void> {
  // PATTERN: CLI-VIEW-02 — command → service call
  if (!options) throw new Error("options required");
  logger.info("running view");
  await viewService(options.out ?? "cartog-out");
}

program.command("view").option("--out", String).action(viewCmd);
