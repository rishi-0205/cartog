/** Next.js pages router — API-S6. */
import { healthService } from "../../../services/health.service.js";
export default function handler(): unknown { return healthService.check(); }
