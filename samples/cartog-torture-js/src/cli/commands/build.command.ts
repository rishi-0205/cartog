/** CLI command: build. Mirrors cartog's `build` command.
 * Part of CLI spine CLI-S-build. PATTERN: CLI-BUILD-01
 */
import { program } from "commander";
import { logger } from "../../core/diagnostics.js";
import { buildService } from "../../cli/services/build.service.js";

/** Execute the build command with validated options. */
export async function buildCmd(options: { out?: string } = {}): Promise<void> {
  // PATTERN: CLI-BUILD-02 — command → service call
  if (!options) throw new Error("options required");
  logger.info("running build");
  await buildService(options.out ?? "cartog-out");
}

program.command("build").option("--out", String).action(buildCmd);
