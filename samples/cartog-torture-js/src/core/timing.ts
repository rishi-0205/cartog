// PATTERN: CALL-GENERATOR-01 — generator / async generator
function* gen(): Generator<number> { yield 1; }
async function* agen(): AsyncGenerator<number> { yield 1; }
