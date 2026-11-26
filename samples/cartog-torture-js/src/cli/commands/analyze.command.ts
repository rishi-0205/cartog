/** CLI command: analyze. Mirrors cartog's `analyze` command.
 * Part of CLI spine CLI-S-analyze. PATTERN: CLI-ANALYZE-01
 */
import { program } from "commander";
import { logger } from "../../core/diagnostics.js";
import { analyzeService } from "../../cli/services/analyze.service.js";

/** Execute the analyze command with validated options. */
export async function analyzeCmd(options: { out?: string } = {}): Promise<void> {
  // PATTERN: CLI-ANALYZE-02 — command → service call
  if (!options) throw new Error("options required");
  logger.info("running analyze");
  await analyzeService(options.out ?? "cartog-out");
}

program.command("analyze").option("--out", String).action(analyzeCmd);
