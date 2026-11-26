/** BullMQ queue binding — producer methods. */
import { Queue } from "bullmq";
export const q = new Queue("scorer-persist", { connection: {} });
export async function addJob(name: string, data: unknown): Promise<void> { await q.add(name, data); }
export async function addBulkJobs(jobs: unknown[]): Promise<void> { await q.addBulk(jobs as never); }
