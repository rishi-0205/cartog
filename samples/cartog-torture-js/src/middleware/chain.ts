// PATTERN: MIDDLEWARE-CHAIN-01 — middleware chain uses edges
import express from "express";
const app = express();
app.use(m1);
app.use(m2);
function m1(): void { return; }
function m2(): void { return; }
