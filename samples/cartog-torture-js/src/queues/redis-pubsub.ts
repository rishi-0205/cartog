/** Redis pub/sub — publish/subscribe methods. */
import Redis from "ioredis";
const r = new Redis();
export function publish(ch: string, data: unknown): void { r.publish(ch, JSON.stringify(data)); }
export function subscribe(ch: string, cb: (...a: unknown[]) => void): void { r.subscribe(ch, cb); }
