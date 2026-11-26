/** CLI command: map. Mirrors cartog's `map` command.
 * Part of CLI spine CLI-S-map. PATTERN: CLI-MAP-01
 */
import { program } from "commander";
import { logger } from "../../core/diagnostics.js";
import { mapService } from "../../cli/services/map.service.js";

/** Execute the map command with validated options. */
export async function mapCmd(options: { out?: string } = {}): Promise<void> {
  // PATTERN: CLI-MAP-02 — command → service call
  if (!options) throw new Error("options required");
  logger.info("running map");
  await mapService(options.out ?? "cartog-out");
}

program.command("map").option("--out", String).action(mapCmd);
