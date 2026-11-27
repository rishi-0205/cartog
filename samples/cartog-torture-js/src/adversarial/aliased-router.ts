/** Router imported as default alias. */
import { Router } from "express";
export function innerHandler(req: unknown, res: unknown): unknown { return res; }
const r = Router();
r.get("/inner", innerHandler);
export default r;
