// PATTERN: PLUGIN-DIRECTORY-01 — load plugins from directory
for (const f of readdirSync("src/plugin")) require(f);
declare function readdirSync(p: string): string[];
