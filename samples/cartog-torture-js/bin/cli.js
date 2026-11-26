#!/usr/bin/env node
/**
 * Primary CLI entrypoint for the cartog-torture-js conformance sample.
 * Mirrors cartog's own Typer CLI using commander.js. Every command is a
 * stub with a documented call chain into cli/services/.
 */
import { Command } from "commander";
import { registerCommands } from "../src/cli/registry.js";

/** Bootstrap the CLI and register all mirrored commands. */
function main(): void {
  const program = new Command();
  registerCommands(program);
  program.parse(process.argv);
}

main();
