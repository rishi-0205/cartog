/** File read utility — file spines. */
import { readFileSync } from "fs";
export function readConfig(path: string): string { return readFileSync(path, "utf-8"); }
