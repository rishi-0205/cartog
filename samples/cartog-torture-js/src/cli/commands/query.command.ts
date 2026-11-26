/** CLI command: query. Mirrors cartog's `query` command.
 * Part of CLI spine CLI-S-query. PATTERN: CLI-QUERY-01
 */
import { program } from "commander";
import { logger } from "../../core/diagnostics.js";
import { queryService } from "../../cli/services/query.service.js";

/** Execute the query command with validated options. */
export async function queryCmd(options: { out?: string } = {}): Promise<void> {
  // PATTERN: CLI-QUERY-02 — command → service call
  if (!options) throw new Error("options required");
  logger.info("running query");
  await queryService(options.out ?? "cartog-out");
}

program.command("query").option("--out", String).action(queryCmd);
