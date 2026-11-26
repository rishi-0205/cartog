/** Express router — middleware chain and serves edges. */
import { Router } from "express";
const router = Router();
router.post("/score-update", authMw, validateMw, scoreUpdate);
router.get("/:id", getMatch);
function authMw(): void { return; }
function validateMw(): void { return; }
function scoreUpdate(): void { return; }
function getMatch(): void { return; }
export default router;
