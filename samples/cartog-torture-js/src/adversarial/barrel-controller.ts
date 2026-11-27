/** Controller calling svc.handle through wildcard barrel. */
import { svc } from "./barrel.js";
export function barrelController(data: unknown): unknown { return svc.handle(data); }
