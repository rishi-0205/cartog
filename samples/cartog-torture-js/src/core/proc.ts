/** Subprocess runner — demonstrates proc whitelist and exception ref_kind. */
import { logger } from "./diagnostics.js";
export async function runCommand(bin: string, args: string[]): Promise<number> {
  if (!bin) throw new Error("empty binary");
  try {
    logger.info(`${bin} ${args.join(" ")}`);
    return 0;
  } catch (err) {
    logger.error(`failed: ${err}`);
    return 1;
  }
}
