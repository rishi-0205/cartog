/** app.use with aliased default import + inline arrow handler. */
import express from "express";
import aliasedRouter from "./aliased-router.js";
const app = express();
app.use("/api/v1/adversarial", aliasedRouter);
app.get("/api/v1/adversarial/health", (req, res) => res.send("ok"));
