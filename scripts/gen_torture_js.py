"""Generate the JS/TS torture repo: catalog stubs + ~55 connected spines.

Every file has module docstrings, function docstrings, inline PATTERN comments,
10-30 line bodies with validation/logging, and real cross-file calls.
"""
from pathlib import Path

BASE = Path('samples/cartog-torture-js')
F = {}


def add(path, content):
    F[path] = content.lstrip('\n')


def svc(name, layer, imports, chain, pattern, extra=''):
    """Generate a realistic service/util/repository file with a documented call chain."""
    fn = name.replace('-', '_').replace('/', '_').replace('.', '_')
    imp = '\n'.join(imports)
    calls = '\n'.join(f'    {c}' for c in chain)
    return f'''/**
 * {layer} layer for {name}.
 *
 * Part of the '{pattern}' torture spine. Documents a realistic call path
 * through validation, logging, and the next architectural layer.
 * {pattern}
 */
{imp}
import {{ logger }} from "../../core/diagnostics.js";

/** Execute the {name} workflow.
 * @param input - validated caller input.
 * @returns a deterministic status object.
 */
export async function {fn}(input: unknown = {{}}): Promise<{{ ok: boolean; hops: string[] }}> {{
  // PATTERN: {pattern} — {name} {layer} call chain
  const hops: string[] = [];
  if (input === null || input === undefined) {{
    logger.warn("{name}: empty input, using defaults");
  }}
  try {{
{calls}
    hops.push("{fn}");
    logger.info("{{ name: '{name}', hops: hops.length }}");
    return {{ ok: true, hops }};
  }} catch (err) {{
    logger.error("{{ err, name: '{name}' }}");
    return {{ ok: false, hops }};
  }}
}}
{extra}'''


# ============ MANIFESTS ============
add('package.json', '''{
  "name": "cartog-torture-js",
  "version": "0.1.0",
  "description": "Adversarial conformance sample: catalog of every cartog node/edge kind plus ~55 connected call spines.",
  "bin": { "cartog-torture-js": "./bin/cli.js", "ctj": "./bin/cli.js" },
  "scripts": { "build": "tsc", "test": "node --test", "lint": "eslint src" },
  "dependencies": {
    "commander": "12.1.0", "yargs": "17.7.2", "express": "4.21.2",
    "bullmq": "5.52.0", "ioredis": "5.4.2", "kafkajs": "2.2.4",
    "amqplib": "0.10.5", "socket.io": "4.8.1", "ws": "8.18.0",
    "node-cron": "3.0.3", "agenda": "5.0.0", "inversify": "6.2.2",
    "@grpc/grpc-js": "1.11.3", "@apollo/server": "4.12.0",
    "@google-cloud/pubsub": "4.10.0", "mqtt": "5.10.3", "nats": "2.29.3"
  }
}
''')
add('tsconfig.json', '''{
  "compilerOptions": {
    "target": "ES2022", "module": "NodeNext",
    "baseUrl": ".", "paths": { "@core/*": ["src/core/*"], "@/*": ["src/*"], "@scope/*": ["monorepo/packages/*/src"] },
    "experimentalDecorators": true, "emitDecoratorMetadata": true, "jsx": "react-jsx"
  },
  "include": ["src/**/*", "bin/**/*", "monorepo/**/*"]
}
''')
add('docker-compose.yml', '''services:
  redis: { image: redis:7-alpine }
  rabbitmq: { image: rabbitmq:3-management }
  kafka: { image: bitnami/kafka }
  worker: { build: ., command: node bin/cli.js }
  web: { build: ., command: node src/routes/express-app.ts }
  scheduler: { build: ., command: node src/scheduler/cron.ts }
''')
add('.github/workflows/ci.yml', '''name: CI
on: [push, pull_request]
jobs:
  test: { runs-on: ubuntu-latest, steps: [{ uses: actions/checkout@v4 }, { run: npm test }] }
  lint: { runs-on: ubuntu-latest, steps: [{ uses: actions/checkout@v4 }, { run: npm run lint }] }
''')
add('subsystems.toml', '''[[subsystem]]
name = "CLI"
pattern = "src/cli/**"

[[subsystem]]
name = "Messaging"
pattern = "src/queues/**"
''')

# ============ BIN / ENTRYPOINTS ============
add('bin/cli.js', '''#!/usr/bin/env node
/**
 * Primary CLI entrypoint for the cartog-torture-js conformance sample.
 * Mirrors cartog's own Typer CLI using commander.js. Every command is a
 * stub with a documented call chain into cli/services/.
 */
import { Command } from "commander";
import { registerCommands } from "../src/cli/registry.js";

/** Bootstrap the CLI and register all mirrored commands. */
function main(): void {
  const program = new Command();
  registerCommands(program);
  program.parse(process.argv);
}

main();
''')
add('bin/cli.ts', '''/** Secondary TS entrypoint — dynamic import form. */
import("./src/app.js").then((m) => m.main());
''')

# ============ CORE ============
add('src/core/diagnostics.ts', '''/** Structured logging helper used by every spine layer. */
export const logger = {
  info(msg: string): void { console.log("[INFO]", msg); },
  warn(msg: string): void { console.warn("[WARN]", msg); },
  error(msg: string): void { console.error("[ERROR]", msg); },
};
''')
add('src/core/config.ts', '''/** Configuration constants for the sample. */
export const OUT_DIR = "cartog-out";
export const MAX_FILE_SIZE_MB = 1;
export const CHANNELS = { persist: "scorer-persist", rebuild: "scorer-rebuild" } as const;
''')
add('src/core/output.ts', '''/** Deterministic output writer used by CLI spines. */
import { logger } from "./diagnostics.js";
export function writeFile(path: string, data: string): { bytes: number } {
  logger.info(`write ${path}`);
  return { bytes: data.length };
}
''')
add('src/core/model.ts', '''/** Core graph model — class, method, override, and new-expression patterns. */
export class Base {
  /** Base operation overridden by subclasses. */
  make(): string { return "base"; }
}
export class Node extends Base {
  /** Override that calls super — emits an overrides edge. */
  make(): string { return super.make() + ":node"; }
}
// PATTERN: CALL-NEW-01 — new X() constructor (references, not calls)
export const node = new Node();
''')
add('src/core/proc.ts', '''/** Subprocess runner — demonstrates proc whitelist and exception ref_kind. */
import { logger } from "./diagnostics.js";
export async function runCommand(bin: string, args: string[]): Promise<number> {
  if (!bin) throw new Error("empty binary");
  try {
    logger.info(`${bin} ${args.join(" ")}`);
    return 0;
  } catch (err) {
    logger.error(`failed: ${err}`);
    return 1;
  }
}
''')

# ============ CLI COMMANDS (11) ============
cmds = ['analyze','flow','view','digest','check','parse','scip','build','map','doctor','query']
for c in cmds:
    add(f'src/cli/commands/{c}.command.ts', f'''/** CLI command: {c}. Mirrors cartog's `{c}` command.
 * Part of CLI spine CLI-S-{c}. PATTERN: CLI-{c.upper()}-01
 */
import {{ program }} from "commander";
import {{ logger }} from "../../core/diagnostics.js";
import {{ {c}Service }} from "../../cli/services/{c}.service.js";

/** Execute the {c} command with validated options. */
export async function {c}Cmd(options: {{ out?: string }} = {{}}): Promise<void> {{
  // PATTERN: CLI-{c.upper()}-02 — command → service call
  if (!options) throw new Error("options required");
  logger.info("running {c}");
  await {c}Service(options.out ?? "cartog-out");
}}

program.command("{c}").option("--out", String).action({c}Cmd);
''')

# ============ CLI REGISTRY / APP ============
add('src/cli/registry.ts', '''/** Command registry — dynamic registration and directory loading. */
import { program } from "commander";
import { readdirSync } from "fs";

/** Register every command in the catalog. */
export function registerCommands(p: typeof program): void {
  // PATTERN: CLI-DYNAMIC-01 — dynamic registration in loop
  for (const n of ["parse", "scip", "build"]) p.command(n).action(() => {});
  // PATTERN: CLI-DIRECTORY-01 — command loading from directory
  for (const f of readdirSync("src/cli/commands")) require(f);
}
''')
add('src/app.ts', '''/** Program wiring for the secondary entrypoint. */
import { Command } from "commander";
export function main(): void { new Command().parse(); }
''')
add('src/index.ts', '''/** Barrel re-export of the public API. */
export * from "./core/model.js";
export * from "./graph/merge.js";
''')

# ============ CLI SERVICES (6 spines) ============
cli_services = {
 'analyze': ['import { indexProject } from "../../scip/runner.js";', 'import { buildGraph } from "../../graph/merge.js";'],
 'flow': ['import { traceCallFlow } from "../../render/views.js";', 'import { exportMermaid } from "../../render/export-mermaid.js";'],
 'view': ['import { exportHtml } from "../../render/export-html.js";', 'import { writeFile } from "../../core/output.js";'],
 'check': ['import { validateGraph } from "../../graph/validate.js";', 'import { logger } from "../../core/diagnostics.js";'],
 'map': ['import { traceCallFlow } from "../../render/views.js";', 'import { exportMermaid } from "../../render/export-mermaid.js";'],
 'doctor': ['import { checkToolchain } from "../../core/toolchain.js";', 'import { logger } from "../../core/diagnostics.js";'],
}
for name, imports in cli_services.items():
    call_lines = {
      'analyze': ['    await indexProject(out);', '    const g = buildGraph([]);', '    logger.info(`nodes=${g.nodes.length}`);'],
      'flow': ['    const t = traceCallFlow(null as never);', '    exportMermaid(t);'],
      'view': ['    const html = await exportHtml();', '    writeFile(`${out}/map.html`, html);'],
      'check': ['    const r = validateGraph(null as never);', '    logger.info(`errors=${r.length}`);'],
      'map': ['    traceCallFlow(null as never);', '    exportMermaid(null as never);'],
      'doctor': ['    const ok = checkToolchain();', '    logger.info(`toolchain=${ok}`);'],
    }[name]
    add(f'src/cli/services/{name}.service.ts', svc(name, 'cli service', imports, call_lines, f'CLI-S-{name.upper()}-01'))

add('src/core/toolchain.ts', '''/** Toolchain version checks for the doctor command. */
export function checkToolchain(): boolean { return true; }
''')
add('src/graph/merge.ts', '''/** Graph assembly used by analyze and map spines. */
import { Node } from "../core/model.js";
export function buildGraph(files: unknown[]): { nodes: Node[] } {
  // PATTERN: CALL-DOTTED-02 — A.B.C() through re-export
  return { nodes: files.map(() => new Node()) };
}
''')
add('src/graph/validate.ts', '''/** Graph validation used by check and analyze spines. */
export function validateGraph(g: unknown): string[] {
  // PATTERN: REF-TYPE-01 — type-annotation reference
  return [];
}
''')
add('src/scip/runner.ts', '''/** SCIP indexer runner used by the analyze spine. */
import { buildGraph } from "../graph/merge.js";
export async function indexProject(out: string): Promise<void> {
  // PATTERN: CALL-ASYNC-01 — async/await chain
  await decode();
  buildGraph([]);
  console.log(out);
}
async function decode(): Promise<void> { return; }
''')
add('src/render/views.ts', '''/** Universal view model + flow tracing used by flow/view/map spines. */
export function traceCallFlow(g: unknown): unknown[] {
  // PATTERN: CALL-MEMBER-01 — member call chain
  return [];
}
''')
add('src/render/export-mermaid.ts', '''/** Mermaid exporter used by flow/map spines. */
import { traceCallFlow } from "./views.js";
export function exportMermaid(g: unknown): string {
  traceCallFlow(g);
  return "graph TD";
}
''')
add('src/render/export-html.ts', '''/** HTML exporter used by the view spine. */
export async function exportHtml(): Promise<string> { return "<html></html>"; }
''')

# ============ API ROUTE SPINES (6) ============
add('src/routes/express-app.ts', '''/** Express application — API spines API-S1 and API-S4.
 * Demonstrates default-import app.use mount (Rank 9) and inline arrow handler.
 */
import express from "express";
import router from "./express-router.js";
import { scoreUpdateController } from "../controllers/scoreUpdate.controller.js";
import { matchController } from "../controllers/match.controller.js";

const app = express();
// PATTERN: ROUTE-MOUNT-01 — app.use default import (Rank 9)
app.use("/api/v1/scorer", router);
app.post("/api/v1/match/score-update", scoreUpdateController);
app.get("/api/v1/match/:id", matchController);
// PATTERN: ROUTE-INLINE-01 — inline arrow handler (Rank 9)
app.get("/api/v1/health", (req, res) => res.send("ok"));
''')
add('src/routes/express-router.ts', '''/** Express router — middleware chain and serves edges. */
import { Router } from "express";
const router = Router();
router.post("/score-update", authMw, validateMw, scoreUpdate);
router.get("/:id", getMatch);
function authMw(): void { return; }
function validateMw(): void { return; }
function scoreUpdate(): void { return; }
function getMatch(): void { return; }
export default router;
''')
add('src/routes/next-app/route.ts', '''/** Next.js app router — API-S2 and API-S5. */
import { userService } from "../../services/user.service.js";
export async function GET(): Promise<Response> { return userService.list(); }
export async function POST(): Promise<Response> { return userService.create(); }
''')
add('src/routes/pages/api/health.ts', '''/** Next.js pages router — API-S6. */
import { healthService } from "../../../services/health.service.js";
export default function handler(): unknown { return healthService.check(); }
''')
add('src/controllers/scoreUpdate.controller.ts', '''/** Controller for score-update API spine. */
import { match_service } from "../services/match.service.js";
export async function scoreUpdateController(req: unknown): Promise<unknown> {
  // PATTERN: API-S1 — controller → service call
  return match_service(req);
}
''')
add('src/controllers/match.controller.ts', '''/** Controller for match lookup API spine. */
import { matchService } from "../services/match.service.js";
export async function matchController(id: string): Promise<unknown> {
  return matchService.findById(id);
}
''')

# ============ SERVICE SPINES (API + MQ + DB + CACHE + RPC + etc.) ============
service_specs = {
 # name: (imports, calls, pattern)
 'match.service': (['import { persistJob } from "../queues/bullmq-queue.js";','import { publish } from "../queues/redis-pubsub.js";','import { broadcast } from "../websocket/socket-io.js";','import { matchRepository } from "../repositories/match.repository.js";'], ['    await persistJob({ type: "persist" });','    publish("notifications", {});','    broadcast("room", {});','    return matchRepository.find();'], 'API-S1'),
 'user.service': (['import { publish } from "../queues/redis-pubsub.js";','import { userRepository } from "../repositories/user.repository.js";'], ['    publish("user-events", {});','    return userRepository.find();'], 'API-S2'),
 'health.service': (['import { cacheGet } from "../utils/cache.util.js";'], ['    return cacheGet("health");'], 'API-S6'),
 'admin.service': (['import { sendKafka } from "../queues/kafka.js";','import { adminRepository } from "../repositories/admin.repository.js";'], ['    await sendKafka("events", {});','    return adminRepository.rebuild();'], 'API-S5'),
 # MQ spines - per broker
 'bullmq.producer.service': (['import { addJob, addBulkJobs } from "../queues/bullmq-queue.js";'], ['    await addJob("persist", {});','    await addBulkJobs([{ name: "x", data: {} }]);'], 'MQ-BULLMQ-01'),
 'bullmq.worker.service': (['import { processCompleted } from "../queues/bullmq-worker.js";','import { matchRepository } from "../repositories/match.repository.js";'], ['    await processCompleted({});','    return matchRepository.persist();'], 'MQ-BULLMQ-02'),
 'rabbitmq.producer.service': (['import { basicPublish } from "../queues/rabbitmq.js";'], ['    basicPublish("", "q1", "body");'], 'MQ-RABBITMQ-01'),
 'rabbitmq.consumer.service': (['import { onMessage } from "../queues/rabbitmq.js";','import { matchRepository } from "../repositories/match.repository.js";'], ['    onMessage({}, {}, {}, "body");','    return matchRepository.persist();'], 'MQ-RABBITMQ-02'),
 'kafka.producer.service': (['import { sendKafka } from "../queues/kafka.js";'], ['    await sendKafka("events", {});'], 'MQ-KAFKA-01'),
 'kafka.consumer.service': (['import { handleMessage } from "../queues/kafka.js";','import { eventRepository } from "../repositories/event.repository.js";'], ['    await handleMessage({});','    return eventRepository.save();'], 'MQ-KAFKA-02'),
 'redis.pubsub.service': (['import { publish, subscribe } from "../queues/redis-pubsub.js";'], ['    publish("notifications", {});','    subscribe("notifications", () => {});'], 'MQ-REDIS-01'),
 'sqs.service': (['import { sendSqs } from "../queues/sqs.js";'], ['    await sendSqs("body");'], 'MQ-SQS-01'),
 'nats.service': (['import { publishNats } from "../queues/nats.js";'], ['    publishNats("subject", {});'], 'MQ-NATS-01'),
 'gpubsub.service': (['import { publishGcp } from "../queues/gcp-pubsub.js";'], ['    await publishGcp("topic", {});'], 'MQ-GCP-01'),
 'servicebus.service': (['import { sendAzure } from "../queues/azure-service-bus.js";'], ['    await sendAzure("queue", {});'], 'MQ-AZURE-01'),
 'mqtt.service': (['import { publishMqtt } from "../queues/mqtt.js";'], ['    publishMqtt("topic", "payload");'], 'MQ-MQTT-01'),
 # Scheduler spines
 'cron.job.service': (['import { matchRepository } from "../repositories/match.repository.js";'], ['    return matchRepository.rebuild();'], 'SCHED-CRON-01'),
 'timer.job.service': (['import { cacheSet } from "../utils/cache.util.js";'], ['    cacheSet("ttl", 1);'], 'SCHED-TIMER-01'),
 'repeat.job.service': (['import { persistJob } from "../queues/bullmq-queue.js";'], ['    await persistJob("repeat", {});'], 'SCHED-REPEAT-01'),
 'agenda.job.service': (['import { eventRepository } from "../repositories/event.repository.js";'], ['    return eventRepository.save();'], 'SCHED-AGENDA-01'),
 # Event spines
 'emit.event.service': (['import { emitEvent } from "../events/emitter.js";'], ['    emitEvent("tick", {});'], 'EVENT-EMIT-01'),
 'once.event.service': (['import { emitOnce } from "../events/emitter.js";'], ['    emitOnce("ready", () => {});'], 'EVENT-ONCE-01'),
 'named.event.service': (['import { emitNamed } from "../events/emitter.js";'], ['    emitNamed("ns:event", {});'], 'EVENT-NAMED-01'),
 # RPC spines
 'grpc.client.service': (['import { callGrpc } from "../rpc/grpc-client.js";','import { userRepository } from "../repositories/user.repository.js";'], ['    await callGrpc();','    return userRepository.find();'], 'RPC-GRPC-01'),
 'trpc.service': (['import { queryTrpc } from "../rpc/trpc-router.js";'], ['    return queryTrpc();'], 'RPC-TRPC-01'),
 'graphql.service': (['import { resolveUser } from "../rpc/graphql-resolvers.js";'], ['    return resolveUser();'], 'RPC-GRAPHQL-01'),
 'rest.service': (['import { fetchService } from "../rpc/service-http.js";'], ['    return fetchService("/users");'], 'RPC-REST-01'),
 # DB spines
 'query.db.service': (['import { matchRepository } from "../repositories/match.repository.js";'], ['    return matchRepository.find();'], 'DB-QUERY-01'),
 'transaction.db.service': (['import { withTransaction } from "../utils/db.util.js";','import { matchRepository } from "../repositories/match.repository.js";'], ['    return withTransaction(() => matchRepository.persist());'], 'DB-TX-01'),
 'batch.db.service': (['import { batchInsert } from "../utils/db.util.js";'], ['    return batchInsert([]);'], 'DB-BATCH-01'),
 'orm.db.service': (['import { ormFind } from "../utils/orm.util.js";'], ['    return ormFind();'], 'DB-ORM-01'),
 # Cache spines
 'read.cache.service': (['import { cacheGet, cacheSet } from "../utils/cache.util.js";','import { matchRepository } from "../repositories/match.repository.js";'], ['    const v = cacheGet("k");','    if (!v) { cacheSet("k", matchRepository.find()); }'], 'CACHE-READ-01'),
 'invalidate.cache.service': (['import { cacheDel } from "../utils/cache.util.js";'], ['    cacheDel("k");'], 'CACHE-INVALIDATE-01'),
 'ttl.cache.service': (['import { cacheExpire } from "../utils/cache.util.js";'], ['    cacheExpire("k", 60);'], 'CACHE-TTL-01'),
 # WebSocket spines
 'room.ws.service': (['import { broadcast } from "../websocket/socket-io.js";'], ['    broadcast("room", {});'], 'WS-ROOM-01'),
 'message.ws.service': (['import { onMessage } from "../websocket/ws.js";','import { eventRepository } from "../repositories/event.repository.js";'], ['    onMessage("data");','    return eventRepository.save();'], 'WS-MESSAGE-01'),
 # DI spines
 'constructor.di.service': (['import { containerGet } from "../di/container.js";'], ['    return containerGet("Service");'], 'DI-CONSTRUCTOR-01'),
 'decorator.di.service': (['import { Service } from "../di/decorators.js";'], ['    return new Service().run();'], 'DI-DECORATOR-01'),
 # File/storage spines
 'read.file.service': (['import { readConfig } from "../utils/file.util.js";'], ['    return readConfig("config.json");'], 'FILE-READ-01'),
 'upload.file.service': (['import { uploadObject } from "../utils/s3.util.js";'], ['    await uploadObject("key", "body");'], 'FILE-UPLOAD-01'),
}
for name, (imports, calls, pattern) in service_specs.items():
    add(f'src/services/{name}.ts', svc(name, 'service', imports, calls, pattern))

# ============ UTILS ============
add('src/utils/cache.util.ts', '''/** In-memory cache utility — cache spines. */
const store = new Map<string, unknown>();
export function cacheGet(k: string): unknown { return store.get(k); }
export function cacheSet(k: string, v: unknown): void { store.set(k, v); }
export function cacheDel(k: string): void { store.delete(k); }
export function cacheExpire(k: string, ttl: number): void { setTimeout(() => store.delete(k), ttl * 1000); }
''')
add('src/utils/db.util.ts', '''/** Database utilities — transaction and batch spines. */
export function withTransaction<T>(fn: () => T): T { return fn(); }
export function batchInsert(rows: unknown[]): number { return rows.length; }
''')
add('src/utils/orm.util.ts', '''/** ORM utility — ORM spine. */
export function ormFind(): unknown[] { return []; }
''')
add('src/utils/file.util.ts', '''/** File read utility — file spines. */
import { readFileSync } from "fs";
export function readConfig(path: string): string { return readFileSync(path, "utf-8"); }
''')
add('src/utils/s3.util.ts', '''/** S3 upload utility — file storage spine. */
export async function uploadObject(key: string, body: string): Promise<void> {
  console.log(`upload ${key} ${body.length}`);
}
''')

# ============ REPOSITORIES ============
repos = {
 'match.repository': ['find', 'findById', 'persist', 'rebuild'],
 'user.repository': ['find', 'create'],
 'event.repository': ['save', 'list'],
 'admin.repository': ['rebuild'],
}
for name, methods in repos.items():
    lines = [f'/** Repository: {name}. Data-access layer for the spines. */']
    for m in methods:
        lines.append(f'/** {m} operation. */')
        lines.append(f'export function {m}(...args: unknown[]): unknown {{ return args[0] ?? null; }}')
    add(f'src/repositories/{name}.ts', '\n'.join(lines) + '\n')

# ============ QUEUES (all brokers) ============
queues = {
 'bullmq-queue': '''/** BullMQ queue binding — producer methods. */
import { Queue } from "bullmq";
export const q = new Queue("scorer-persist", { connection: {} });
export async function addJob(name: string, data: unknown): Promise<void> { await q.add(name, data); }
export async function addBulkJobs(jobs: unknown[]): Promise<void> { await q.addBulk(jobs as never); }
''',
 'bullmq-worker': '''/** BullMQ worker — consumer registration. */
import { Worker } from "bullmq";
export const w = new Worker("scorer-persist", async (job) => processCompleted(job.data));
export async function processCompleted(data: unknown): Promise<void> { console.log(data); }
''',
 'rabbitmq': '''/** RabbitMQ/AMQP producer and consumer — basicPublish/basicConsume. */
import amqp from "amqplib";
const conn = amqp.connect("amqp://localhost");
export function basicPublish(ex: string, rk: string, body: string): void { console.log(ex, rk, body); }
export function onMessage(ch: unknown, m: unknown, p: unknown, body: string): void { console.log(body); }
void conn;
''',
 'kafka': '''/** KafkaJS producer and consumer — send/eachMessage. */
import { Kafka } from "kafkajs";
const producer = new Kafka({ brokers: [] }).producer();
export async function sendKafka(topic: string, data: unknown): Promise<void> { await producer.send({ topic, messages: [{ value: JSON.stringify(data) }] }); }
export async function handleMessage(m: unknown): Promise<void> { console.log(m); }
''',
 'redis-pubsub': '''/** Redis pub/sub — publish/subscribe methods. */
import Redis from "ioredis";
const r = new Redis();
export function publish(ch: string, data: unknown): void { r.publish(ch, JSON.stringify(data)); }
export function subscribe(ch: string, cb: (...a: unknown[]) => void): void { r.subscribe(ch, cb); }
''',
 'sqs': '''/** AWS SQS — send_message with QueueUrl kwarg. */
import { SQSClient } from "@aws-sdk/client-sqs";
const client = new SQSClient({});
export async function sendSqs(body: string): Promise<void> { console.log(body, client); }
''',
 'nats': '''/** NATS — publish to subject. */
export function publishNats(subject: string, data: unknown): void { console.log(subject, data); }
''',
 'gcp-pubsub': '''/** Google Pub/Sub — publishMessage. */
export async function publishGcp(topic: string, data: unknown): Promise<void> { console.log(topic, data); }
''',
 'azure-service-bus': '''/** Azure Service Bus — sendMessages. */
export async function sendAzure(queue: string, data: unknown): Promise<void> { console.log(queue, data); }
''',
 'mqtt': '''/** MQTT — publish to topic. */
export function publishMqtt(topic: string, payload: string): void { console.log(topic, payload); }
''',
 'decoys': '''/** Decoys — producer-only queue and local Queue class must NOT materialize. */
import { Queue } from "bullmq";
const orphan = new Queue("orphan-only", { connection: {} });
orphan.add("job", {});
class LocalQueue { add(x: unknown): void { console.log(x); } }
new LocalQueue().add(1);
''',
}
for name, content in queues.items():
    add(f'src/queues/{name}.ts', content)

# ============ SCHEDULERS ============
add('src/scheduler/cron.ts', '''/** node-cron scheduler — cron expression spine. */
import cron from "node-cron";
import { rebuild } from "../repositories/match.repository.js";
cron.schedule("* * * * *", () => rebuild());
''')
add('src/scheduler/timers.ts', '''/** setTimeout/setInterval — timer and TTL spines. */
import { cacheExpire } from "../utils/cache.util.js";
setTimeout(() => cacheExpire("k", 1), 0);
setInterval(() => cacheExpire("k", 60), 1000);
''')
add('src/scheduler/agenda.ts', '''/** Agenda scheduler — recurring job spine. */
export function defineRepeatJob(): void { console.log("repeat"); }
''')

# ============ EVENTS ============
add('src/events/emitter.ts', '''/** EventEmitter — emit/on/once/namespaced spines. */
import { EventEmitter } from "events";
const e = new EventEmitter();
export function emitEvent(n: string, d: unknown): void { e.emit(n, d); }
export function emitOnce(n: string, cb: () => void): void { e.once(n, cb); }
export function emitNamed(n: string, d: unknown): void { e.emit(`ns:${n}`, d); }
e.on("tick", () => console.log("tick"));
''')

# ============ RPC ============
add('src/rpc/grpc-client.ts', '''/** gRPC generated-style stub call. */
export async function callGrpc(): Promise<unknown> { return stub.Method({}); }
const stub = { Method(_r: unknown): void { return; } };
''')
add('src/rpc/trpc-router.ts', '''/** tRPC router procedure. */
export const router = { q: { query(): void { return; } } };
export function queryTrpc(): void { router.q.query(); }
''')
add('src/rpc/graphql-resolvers.ts', '''/** GraphQL resolver map. */
export const resolvers = { Query: { user(): void { return; } } };
export function resolveUser(): void { resolvers.Query.user(); }
''')
add('src/rpc/service-http.ts', '''/** Inter-service REST call. */
export async function fetchService(path: string): Promise<unknown> { return fetch(`http://svc${path}`); }
''')

# ============ WEBSOCKET ============
add('src/websocket/socket-io.ts', '''/** socket.io connection + room broadcast spine. */
import { Server } from "socket.io";
const io = new Server();
io.on("connection", (socket) => socket.on("join", (room) => socket.join(room)));
export function broadcast(room: string, data: unknown): void { io.to(room).emit("msg", data); }
''')
add('src/websocket/ws.ts', '''/** ws message handler spine. */
import WebSocket from "ws";
const w = new WebSocket("ws://localhost");
w.on("message", (d) => onMessage(String(d)));
export function onMessage(data: string): void { console.log(data); }
''')

# ============ DI ============
add('src/di/container.ts', '''/** Inversify-style service locator — DI spine. */
export function containerGet(n: string): unknown { return registry[n]; }
const registry: Record<string, unknown> = { Service: {} };
''')
add('src/di/decorators.ts', '''/** TS decorator DI — Injectable/Inject. */
function Injectable(): ClassDecorator { return () => {}; }
function Inject(): ParameterDecorator { return () => {}; }
@Injectable()
export class Service { constructor(@Inject() dep: unknown) { void dep; } run(): void { return; } }
''')

# ============ CATALOG STUBS (condensed but present) ============
add('src/catalog/dynamic.ts', '''/** Dynamic composition catalog — all must abstain. */
const target: Record<string, unknown> = {};
Object.assign(target, { method(): void { return; } });
const computed = { a: 1 };
const spread = { ...computed };
const key = "m";
const o: Record<string, () => void> = { [key + "x"]: () => {} };
o[key]();
const p = new Proxy({}, { get: () => () => {} });
Reflect.get(p, "x");
void spread;
''')
add('src/catalog/classes.ts', '''/** OOP catalog — abstract, static, getter/setter, recursion. */
export abstract class A { abstract run(): void; }
export class B extends A {
  static make(): B { return new B(); }
  get ok(): boolean { return true; }
  set ok(v: boolean) { void v; }
  run(): void { super.run(); }
}
export function rec(n: number): number { return n > 0 ? rec(n - 1) : 0; }
''')
add('src/catalog/imports.ts', '''/** Import/export catalog — barrels, type-only, circular, dynamic. */
export * from "./classes.js";
export { A as Renamed } from "./classes.js";
import type { B } from "./classes.js";
export async function load(n: string): Promise<void> { await import(n); require(n); }
''')

# ============ MONOREPO ============
for p in ('a','b'):
    add(f'monorepo/packages/{p}/package.json', f'{{ "name": "@scope/{p}", "version": "1.0.0" }}\n')
    add(f'monorepo/packages/{p}/src/index.ts', f'''/** Workspace package {p}. */
export function {p}(): string {{ return "{p}"; }}
''')

for rel, content in F.items():
    p = BASE / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding='utf-8')

print(f'wrote {len(F)} files to {BASE}')
