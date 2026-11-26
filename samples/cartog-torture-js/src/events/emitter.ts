/** EventEmitter — emit/on/once/namespaced spines. */
import { EventEmitter } from "events";
const e = new EventEmitter();
export function emitEvent(n: string, d: unknown): void { e.emit(n, d); }
export function emitOnce(n: string, cb: () => void): void { e.once(n, cb); }
export function emitNamed(n: string, d: unknown): void { e.emit(`ns:${n}`, d); }
e.on("tick", () => console.log("tick"));
