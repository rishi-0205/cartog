/** CLI command: digest. Mirrors cartog's `digest` command.
 * Part of CLI spine CLI-S-digest. PATTERN: CLI-DIGEST-01
 */
import { program } from "commander";
import { logger } from "../../core/diagnostics.js";
import { digestService } from "../../cli/services/digest.service.js";

/** Execute the digest command with validated options. */
export async function digestCmd(options: { out?: string } = {}): Promise<void> {
  // PATTERN: CLI-DIGEST-02 — command → service call
  if (!options) throw new Error("options required");
  logger.info("running digest");
  await digestService(options.out ?? "cartog-out");
}

program.command("digest").option("--out", String).action(digestCmd);
