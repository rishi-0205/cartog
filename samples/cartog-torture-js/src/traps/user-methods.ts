// PATTERN: TRAP-USER-PUBLISH-01 — ordinary publish() with no channel context
export function publish(x: unknown): void { return; }
publish("hello");
