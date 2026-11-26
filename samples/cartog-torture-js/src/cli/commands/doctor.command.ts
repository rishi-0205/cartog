/** CLI command: doctor. Mirrors cartog's `doctor` command.
 * Part of CLI spine CLI-S-doctor. PATTERN: CLI-DOCTOR-01
 */
import { program } from "commander";
import { logger } from "../../core/diagnostics.js";
import { doctorService } from "../../cli/services/doctor.service.js";

/** Execute the doctor command with validated options. */
export async function doctorCmd(options: { out?: string } = {}): Promise<void> {
  // PATTERN: CLI-DOCTOR-02 — command → service call
  if (!options) throw new Error("options required");
  logger.info("running doctor");
  await doctorService(options.out ?? "cartog-out");
}

program.command("doctor").option("--out", String).action(doctorCmd);
