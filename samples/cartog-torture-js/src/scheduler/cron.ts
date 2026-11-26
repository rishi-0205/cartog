/** node-cron scheduler — cron expression spine. */
import cron from "node-cron";
import { rebuild } from "../repositories/match.repository.js";
cron.schedule("* * * * *", () => rebuild());
