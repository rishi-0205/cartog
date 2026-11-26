/** Controller for match lookup API spine. */
import { matchService } from "../services/match.service.js";
export async function matchController(id: string): Promise<unknown> {
  return matchService.findById(id);
}
