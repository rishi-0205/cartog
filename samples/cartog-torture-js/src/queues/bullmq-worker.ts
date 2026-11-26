/** BullMQ worker — consumer registration. */
import { Worker } from "bullmq";
export const w = new Worker("scorer-persist", async (job) => processCompleted(job.data));
export async function processCompleted(data: unknown): Promise<void> { console.log(data); }
