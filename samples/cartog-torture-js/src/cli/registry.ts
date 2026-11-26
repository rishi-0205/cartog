/** Command registry — dynamic registration and directory loading. */
import { program } from "commander";
import { readdirSync } from "fs";

/** Register every command in the catalog. */
export function registerCommands(p: typeof program): void {
  // PATTERN: CLI-DYNAMIC-01 — dynamic registration in loop
  for (const n of ["parse", "scip", "build"]) p.command(n).action(() => {});
  // PATTERN: CLI-DIRECTORY-01 — command loading from directory
  for (const f of readdirSync("src/cli/commands")) require(f);
}
