// PATTERN: CLI-HOOK-01 — preAction hook middleware
program.hook("preAction", (thisCommand) => { preAction(); });
function preAction(): void { return; }
