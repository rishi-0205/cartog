# Adversarial Torture Codebases — Final Plan

**Branch:** `test/adversarial-samples` (from `main`)
**Date:** 2026-11-26
**Status:** IMPLEMENTING

---

## 1. Goal

Two dummy repos — one JS/TS, one Python — that are conformance fixtures for
cartog. They must:

1. **Look and feel like real codebases** — multi-folder package layout, module
   docstrings, function docstrings, inline comments, 10–30 line function bodies
   with validation/try-catch/logging, cross-file/cross-folder/in-file calls,
   controller → service → util → repository → sink chains.
2. **Mirror cartog's own CLI** (`analyze`, `flow`, `view`, `digest`, `check`,
   `parse`, `scip`, `build`, `map`, `doctor`, `query`).
3. **Have a catalog layer** — every node/edge/ref_kind/confidence kind cartog can
   emit, as labeled stubs with `PATTERN:` markers.
4. **Have a spine layer** — ~55 independently traceable call chains per repo
   covering CLI, API routes, MQs (all brokers × all methods), schedulers,
   events, RPC, databases, caches, websockets, DI, file/storage.
5. **Detect decorators too** — every Python decorator type must emit a
   `references` edge with `ref_kind: "decorator"` (including DI decorators — no
   abstention for decorators).
6. **Cover every method variant** — all producer/consumer methods per broker.
7. **Use multiple implementations per component** — BullMQ, RabbitMQ, Kafka,
   Redis, SQS, Celery, NATS, GCP Pub/Sub, Azure Service Bus, MQTT, etc.

The repos exist to be *parsed*, not run. Size is not a constraint.

---

## 2. Node & edge catalog (must all appear across both repos)

**Nodes:** file, folder, class, function, method, route, command, entrypoint,
middleware, service, ci_job, dependency, channel, worker, processor,
script, npm_script, gui_script, subsystem, helper_group

**Edges:** contains, imports, depends_on, calls, references, overrides,
serves, starts, uses, produces, consumes

**ref_kinds:** decorator, exception, isinstance, inheritance, type, callback, other

**confidence:** resolved, reconciled, import, heuristic, inferred

---

## 3. Message queue method catalog (both repos)

### Producer methods (all)
`add`, `addBulk`, `send`, `send_messages`, `publish`, `publishMessage`,
`put`, `push`, `send_task`, `delay`, `apply_async`, `emit`, `enqueue`,
`send_message`, `sendMessages`, `basic_publish`, `sendToQueue`

### Consumer methods (all)
`on`, `once`, `subscribe`, `consume`, `basic_consume`, `listen`, `receive`,
`get`, `poll`, `eachMessage`, `forEach`, `on_message`, `ack`, `nack`,
`retry`, `moveToCompleted`, `register processor`

### Broker families (multiple implementations each)
- BullMQ (Redis), RabbitMQ/AMQP (amqplib / pika), Kafka (kafkajs / kafka-python),
  Redis pub/sub (ioredis / redis-py), SQS (boto3), Celery, NATS,
  Google Pub/Sub, Azure Service Bus, MQTT (mqtt.js / paho-mqtt)

---

## 4. Python decorator catalog (all must emit `references` + `ref_kind: decorator`)

- CLI: `@app.command()`, `@app.callback()`, `@app.group()`, `@group.command()`,
  `@click.option(callback=fn)`, `@click.pass_context`, `@argparse.set_defaults`
- Route: `@app.get/post/put/delete/patch`, `@router.get`, `@bp.route`,
  `@app.middleware("http")`, `@receiver(signal)`
- Task: `@app.task(name=...)`, `@shared_task`, `@app.task(bind=True)`
- DI: `@Injectable()`, `@Inject()`, `Depends()`, `@provides`, `@singleton`
- OOP: `@property`, `@x.setter`, `@staticmethod`, `@classmethod`,
  `@abstractmethod`, `@dataclass`, `@functools.wraps`, `@contextmanager`,
  `@lru_cache`, `@singledispatch`
- Factories: `@retry(times=3)`, `@rate_limit(10)`, `@cache(ttl=60)`,
  `@transaction(readonly=True)`
- Stacked: `@router.get @auth @cache @validate` on one function
- Class decorators: `@dataclass`, `@Injectable`, `@register`, `@click.group`
- Async decorators: `@app.task` on `async def`

---

## 5. Component catalog (multiple implementations each)

| Component | JS variants | Python variants |
|---|---|---|
| Database | Prisma, Mongoose, pg, SQLite, Drizzle, TypeORM | SQLAlchemy, Django ORM, psycopg2, mongodb, sqlite3, Peewee |
| Cache | Redis, Memcached, in-memory Map, node-cache | Redis, lru_cache, cachetools, Django cache, dict |
| WebSocket | socket.io, ws, native WebSocket | Channels, websockets, python-socketio, FastAPI WS |
| RPC | gRPC, tRPC, GraphQL, REST fetch | gRPC, GraphQL, XML-RPC, httpx |
| Scheduler | node-cron, timers, QueueScheduler, agenda, node-schedule | APScheduler, Celery Beat, BackgroundTasks, schedule |
| Event | EventEmitter, process.on, DOM, RxJS | blinker, Django signals, pyee, asyncio Event |
| DI | TS decorators, inversify, typeDI | Depends, dependency_injector, injector, punq |
| File/Storage | fs, S3, streams | open, pathlib, boto3 S3, pandas, CSV |

---

## 6. Spine catalog (~55 per repo)

Each spine is 5–10 files with cross-file/folder/in-file calls and a real
controller → service → util → repository → sink chain.

**CLI (6):** analyze, flow, view, check, map, doctor — each → cli/services →
cartog modules.
**API routes (6):** Express/Next/FastAPI/Flask/Django/Channels routes →
controller → service → MQs → repository → sink.
**MQ (10–12):** one per broker × producer/consumer methods.
**Scheduler (5):** cron, interval, one-shot, repeat, beat.
**Event (4):** emit/on, once, namespaced, dynamic (abstain).
**RPC (4):** stub, generated client, resolver, REST.
**Database (6):** direct query, transaction, repository, raw SQL, batch, ORM.
**Cache (5):** read-through, write-through, invalidation, TTL, in-memory.
**WebSocket (3):** connect→broadcast, message→db, disconnect→cleanup.
**DI (3):** constructor, parameter, service locator.
**File/Storage (3):** read→parse, write→invalidate, upload→queue.

---

## 7. Real-codebase quality standard (every file)

- Module docstring explaining role
- Function/method docstrings with args + description
- 10–30 line bodies: validation, try/catch, logging, next-layer call, return
- Inline `# PATTERN: <id> — <what it tests>` marker
- Cross-file imports through barrels/`__init__.py`
- Cross-folder calls: cli → services → utils → repositories → sinks
- In-file helper calls
- No network, no randomness, no runtime services needed to parse

---

## 8. Storage & safety

- Repos live in `samples/cartog-torture-js` and `samples/cartog-torture-py`
  (gitignored); generators and ground truth committed under `scripts/` and
  `tests/adversarial/`.
- Old samples (click, flask, ky, webscrapper, fastapi-celery) deleted; fetch
  script + samples.lock updated to pin only the torture repos.
- `samples/` is never modified by cartog (invariant test must stay green).

---

## 9. Ground truth & verification

`expected.json` per repo:
- `catalog` — node/edge/ref/confidence kinds
- `spines` — `expect_path` (exact edge sequence) + `expect_abstain`
- `decorators` — expected `ref_kind`
- `methods` — expected edge kind per method variant

`check_conformance.py` reports:
- catalog coverage
- path completeness / path accuracy per spine
- abstention correctness
- decorator detection rate
- per-method coverage

Evidence saved to `docs/evidence/CONFORMANCE-<repo>-*.txt`.

---

## 10. Implementation order

1. Rewrite this plan to `docs/ADVERSARIAL_SAMPLES.md` ✅ (this file)
2. Delete old samples
3. Build catalog + spine layer in both repos (generators in `scripts/`)
4. Regenerate `expected.json` + `PATTERNS.md`
5. Upgrade `check_conformance.py`
6. Run no-scip + SCIP passes, save evidence
7. Write findings; no commit until asked
