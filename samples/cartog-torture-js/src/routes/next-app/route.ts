/** Next.js app router — API-S2 and API-S5. */
import { userService } from "../../services/user.service.js";
export async function GET(): Promise<Response> { return userService.list(); }
export async function POST(): Promise<Response> { return userService.create(); }
