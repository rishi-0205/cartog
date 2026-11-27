/** Controller for score-update API spine. */
import { match_service } from "../services/match.service.js";
export async function scoreUpdateController(req: unknown): Promise<unknown> {
  // PATTERN: API-S1 — controller → service call
  return match_service(req);
}
