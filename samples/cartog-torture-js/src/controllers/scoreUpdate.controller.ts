/** Controller for score-update API spine. */
import { scoreUpdateService } from "../services/match.service.js";
export async function scoreUpdateController(req: unknown): Promise<unknown> {
  // PATTERN: API-S1 — controller → service call
  return scoreUpdateService.handle(req);
}
