/** Express application — API spines API-S1 and API-S4.
 * Demonstrates default-import app.use mount (Rank 9) and inline arrow handler.
 */
import express from "express";
import router from "./express-router.js";
import { scoreUpdateController } from "../controllers/scoreUpdate.controller.js";
import { matchController } from "../controllers/match.controller.js";

const app = express();
// PATTERN: ROUTE-MOUNT-01 — app.use default import (Rank 9)
app.use("/api/v1/scorer", router);
app.post("/api/v1/match/score-update", scoreUpdateController);
app.get("/api/v1/match/:id", matchController);
// PATTERN: ROUTE-INLINE-01 — inline arrow handler (Rank 9)
app.get("/api/v1/health", (req, res) => res.send("ok"));
