/** CLI command: parse. Mirrors cartog's `parse` command.
 * Part of CLI spine CLI-S-parse. PATTERN: CLI-PARSE-01
 */
import { program } from "commander";
import { logger } from "../../core/diagnostics.js";
import { parseService } from "../../cli/services/parse.service.js";

/** Execute the parse command with validated options. */
export async function parseCmd(options: { out?: string } = {}): Promise<void> {
  // PATTERN: CLI-PARSE-02 — command → service call
  if (!options) throw new Error("options required");
  logger.info("running parse");
  await parseService(options.out ?? "cartog-out");
}

program.command("parse").option("--out", String).action(parseCmd);
