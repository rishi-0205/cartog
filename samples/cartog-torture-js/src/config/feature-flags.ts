// PATTERN: CONFIG-FEATURE-01 — conditional command registration
if (process.env.FEATURE_X) program.command("x");
declare const program: { command(n: string): void };
