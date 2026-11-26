/** Structured logging helper used by every spine layer. */
export const logger = {
  info(msg: string): void { console.log("[INFO]", msg); },
  warn(msg: string): void { console.warn("[WARN]", msg); },
  error(msg: string): void { console.error("[ERROR]", msg); },
};
