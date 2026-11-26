/** Decoys — producer-only queue and local Queue class must NOT materialize. */
import { Queue } from "bullmq";
const orphan = new Queue("orphan-only", { connection: {} });
orphan.add("job", {});
class LocalQueue { add(x: unknown): void { console.log(x); } }
new LocalQueue().add(1);
