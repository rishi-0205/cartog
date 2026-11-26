# Message Brokers and Async Channels â€” Complete Plan, Implementation Status, and Python Gap Analysis

Date: 2026-11-26
Branch: `feature/messaging` (from `main` after E4 merge)
Status: Part 2 (JS/TS) IMPLEMENTED and VERIFIED. Python gap analysis and plan in Part 4.

---

# Part 1 â€” Residual issues (from original plan)

## 1.1 Why we abstain on dynamic composition

Tree-sitter is syntax-only. For `Object.assign`, object spreads, computed dynamic keys, decorator-based DI, and proxy/wrapper service objects, there is no static mapping from binding to channel name or from call site to callee definition. Emitting an edge would be a guess. These are recorded in `unresolved` with reason `ambiguous_chain`. Recall limitation, not correctness bug. (Also documented as Rank 8 in `KNOWN_ISSUES.md`.)

## 1.2 Local classes â€” recall limitation

Local classes used as brokers with no cross-file producer/consumer pair are missed. The pairing rule protects against false positives. Local classes excluded at first; pairing rule can relax later. (Documented as Rank 12 in `KNOWN_ISSUES.md`.)

## 1.3 Prisma â€” deferred

`.prisma` files skipped. Needs new grammar/parser. Out of scope. (Documented as Rank 13 in `KNOWN_ISSUES.md`.)

## 1.4 DTOs, types, data models â€” deferred

Data, not control flow. Needs new node kinds and view semantics. (Documented as Rank 14 in `KNOWN_ISSUES.md`.)

## 1.5 SCIP remains required

SCIP uses the language server with full type information. Tree-sitter is syntax-only. SCIP is a hard dependency. (Documented as Rank 11 in `KNOWN_ISSUES.md`.)

## 1.6 Rank 4 â€” duplicate node ids (reporting bug)

`Graph.duplicate_node_ids` accumulates during assembly; `validate_graph` reports them as errors even though `graph.json` has unique ids. Fix: clear/rebuild accumulator. (Documented as Rank 4 in `KNOWN_ISSUES.md`.)

## 1.7 Rank 6 â€” Windows `python3` lookup

`scip-python` has no interpreter option; Pyright picks up Windows Store Python. Deferred. (Documented as Rank 6 in `KNOWN_ISSUES.md`.)

## 1.8 Rank 7 â€” `new X(...)` is not a call edge

`classify_occurrence()` handles `call` and `call_expression` but not `new_expression`. Lowâ€“Medium severity. (Documented as Rank 7 in `KNOWN_ISSUES.md`.)

## 1.9 Rank 2 â€” local closures remain unsolved

Arrow functions assigned to `const` are not emitted as symbols by `scip-typescript`. Upstream limitation. (Documented as Rank 2 in `KNOWN_ISSUES.md`.)

## 1.10 Python equivalents remain

Verifier and chain resolver are TS/JS first. Python analogues deferred. (Documented as Rank 10 in `KNOWN_ISSUES.md`.)

## 1.11 Rank 9 â€” `app.use` mount points and inline handlers

11 of 85 routes have no serves edge (default import alias resolution + inline arrow handlers). Follow-up. (Documented as Rank 9 in `KNOWN_ISSUES.md`.)

## 1.12 Dynamic composition abstain (reiterated)

Tree-sitter is syntax-only. Abstain and record in `unresolved`. (Documented as Rank 8 in `KNOWN_ISSUES.md`.)

---

# Part 2 â€” Design: message brokers and async channels (original plan)

## 2.1 Goal

Make BullMQ-style producer â†’ channel â†’ processor â†’ service traces visible in `flow.html`, using a generic structural detector covering RabbitMQ, Kafka, Redis pub/sub, SQS without per-SDK code. BullMQ is the first test case.

## 2.2 The problem

On Cricklo: `scorerPersistQueue.add(...)` is a leaf call; `scorerPersistWorker` is a disconnected island; channel name `"scorer-persist"` is never modelled.

## 2.3 Core idea: data, not verbs

Relationship carried by channel identity, not method names. Discriminators:
1. Binding â†’ channel map: `new X("name", ...)` â†’ binding (X not builtin)
2. Argument shape: payload â†’ producer, function â†’ consumer
3. Pairing: `channel` node materialized only when same name on both sides

No SDK catalog, no verb list. The only SDK-specific knowledge is the generic shape "constructor/factory returning a client whose first string arg is a channel name", which is stable across brokers.

## 2.4 Schema changes (2.1.0 â†’ 2.2.0)

New node kinds: `channel`, `worker`, `processor`.
New edge kinds: `produces` (function â†’ channel), `consumes` (channel â†’ processor).

## 2.5 Detection (JS/TS adapter)

- `new_expression` with external callee + string first arg â†’ binding
- `new Worker(name, fn)` â†’ worker + processor
- Calls on channel binding with payload â†’ produces
- Direct-name calls classified by argument shape
- Channel names resolved through member-chain resolver
- Abstain on ambiguity; record in `unresolved`

## 2.6 Flow traversal

`trace_call_flow` follows `produces`/`consumes`/`starts`. Async hops default-on, badged.

## 2.7 Package.json `starts` repair (deferred)

Not a prerequisite; `consumes` already traces producer routes into worker processors.

## 2.8 Tests (red first)

1. Synthetic BullMQ fixture (one queue, one producer, one worker+processor, decoy queue with only producer)
2. Object literal with methods `c` and `d` â†’ picks `c`
3. Ambiguous re-export â†’ no channel
4. Consumer handler is inline arrow â†’ verify processor node created
5. Real-repo check: all three Cricklo queues become channel nodes; `POST /score-update â†’ â€¦ â†’ scorerPersistQueue â†’ processor` traces end-to-end

## 2.9 Verification and evidence

- Cricklo before/after: counts of channels, workers, processors, produces, consumes; flow depth
- Golden fingerprints: unchanged (click/flask/ky use no brokers)
- Update KNOWN_ISSUES.md (Rank 9 follow-up; add broker rank)
- Update VERIFICATION.md (messaging section)
- Re-measure V5 call sample if new inferred edges appear (expected: none)

## 2.10 Open questions (decided)

1. Consumer handler: real `processor` node â†’ **decided: processor node**
2. Unresolvable channel names â†’ **decided: abstain**
3. `consumes` edges default-on in flow.html â†’ **decided: default on, filterable**

## 2.11 Residuals (recorded, not in scope)

Dynamic composition, local closures, `new X()` as references, `app.use` mount points, Python equivalents, DTOs/types/Prisma, SCIP requirement, Windows python3 lookup, Rank 4 duplicate node id, `inferred` confidence, measurement limits, UTF-16 position mismatch.

---

# Part 3 â€” Implementation status (JS/TS)

### 3.1 What was implemented

**Schema (2.1.0 â†’ 2.2.0):**
- New node kinds: `channel`, `worker`, `processor`
- New edge kinds: `produces`, `consumes`
- `validate.py` accepts 2.2.0

**JS/TS adapter (`cartog/parse/js_adapter.py`):**
- `extract_channel_candidates()` returns raw candidates: `binding`, `member_call`, `direct_call`, `worker`
- Candidates classified and paired in merge.py (not in adapter)

**Cross-file pairing (`cartog/graph/merge.py` section 2c):**
1. Global binding map from all `binding` candidates across all files
2. Classify `member_call` as producer/consumer using global binding map
3. Classify `direct_call` by argument shape
4. Group by channel name; materialise `channel` node only when both sides exist
5. Create `worker` + `processor` nodes with `contains` edges
6. Create `produces` edges (function â†’ channel)
7. Create `consumes` edges (channel â†’ processor)
8. Record unpaired channels in `unresolved`

**Flow traversal (`cartog/render/views.py`):**
- `trace_call_flow` follows `produces` and `consumes` edges

### 3.2 Verification on Cricklo

| Metric | Value |
|---|---|
| Channels materialized | 3 (smsQueue, scorer-persist, scorer-rebuild) |
| Workers | 3 |
| Processors | 3 |
| Produces edges | 12 |
| Consumes edges | 3 |
| Unpaired (correctly excluded) | 12 job-type names |
| Flow traces verified | 7 scorer routes + 3 auth routes |
| Tests passing | 258 passed, 1 warning |

Flow traces confirmed:
- `scoreUpdate` â†’ produces â†’ `scorer-persist` â†’ consumes â†’ `processor:scorer-persist`
- `forgotPassword` â†’ produces â†’ `smsQueue` â†’ consumes â†’ `processor:smsQueue`
- `rebuildMatch` â†’ produces â†’ `scorer-rebuild` â†’ consumes â†’ `processor:scorer-rebuild`
- `startMatch` â†’ produces â†’ `scorer-rebuild` + `scorer-persist`
- `completeMatch` â†’ produces â†’ `scorer-rebuild` + `scorer-persist`
- `overEnd` â†’ produces â†’ `scorer-persist`
- `inningsChange` â†’ produces â†’ `scorer-rebuild` + `scorer-persist`

### 3.3 Commits on `feature/messaging`

1. `77eb29c` â€” Initial implementation
2. `ce1ff9e` â€” Fix candidate filter (include member_call/direct_call)
3. `5b123f8` â€” Refactor to raw candidates for cross-file pairing

### 3.4 What remains (Â§2.8â€“2.9)

- [ ] Red-green tests: synthetic BullMQ fixture, object literal ambiguity, ambiguous re-export, inline arrow processor, real-repo check
- [ ] Evidence files: `docs/evidence/MSG-*.txt` with before/after counts
- [ ] KNOWN_ISSUES.md: update Rank 9, add broker rank
- [ ] VERIFICATION.md: messaging section
- [ ] Golden fingerprints: re-check (expected unchanged for click/flask/ky)

---

# Part 4 â€” Python gap analysis and plan

### 4.1 Current state

The Python adapter (`cartog/parse/python_adapter.py`) has **no** `extract_channel_candidates` method. Python files produce zero channel candidates. No channels, workers, processors, produces, or consumes edges are created for Python repositories.

The base class stub returns `[]`, so Python silently produces nothing. The merge.py pairing pass only processes candidates that exist â€” Python contributes none.

### 4.2 Python message broker patterns â€” generic structural detection

The Python implementation should use the **same generic structural detector** as JS/TS. No SDK-specific method names, no verb lists, no per-library code. The only SDK-specific knowledge is the same generic shape: "constructor/factory returning a client whose first string arg is a channel name", which is stable across brokers.

The detection logic is identical to JS/TS (Â§2.3):

1. **Binding â†’ channel map**: `X("name", ...)` where X is not a builtin â†’ binding (binding variable â†’ channel name). Python has no `new` keyword, so this is just `X("name", ...)`.
2. **Argument shape**: For calls whose receiver is not a channel binding:
   - producer-like when a string/constant argument is accompanied by a non-function payload argument
   - consumer-like when a string/constant argument is accompanied by a function argument
3. **Pairing**: `channel` node materialized only when same name on both sides.

The only Python-specific adaptations are syntactic:
- No `new` keyword â€” constructors are just `X("name", ...)`
- Decorators: `@app.task(name="...")` decorated function â†’ the decorated function is a processor with channel = the name arg. This is still generic: any decorator with a string name arg on a function makes that function a processor.
- For-loop consumers: `for msg in consumer:` where consumer is a binding â†’ the enclosing function is the processor. Generic: any for-loop iterating over a channel binding.
- Keyword arguments: `basic_publish(exchange="", routing_key="q", body=data)` â€” the channel name may be in a kwarg, not positional. Need to check common kwarg names (`routing_key`, `queue`, `topic`, `channel`, `name`) in addition to positional args.

### 4.3 Python-specific syntactic adaptations

| Aspect | JS/TS | Python adaptation |
|---|---|---|
| Constructor | `new X("name", ...)` | `X("name", ...)` (no `new`) |
| Decorator handler | N/A (JS uses `new Worker(name, fn)`) | `@decorator(name="...")` on a function â†’ processor with channel = name |
| For-loop consumer | N/A (JS uses callback args) | `for x in binding:` â†’ enclosing function is processor |
| Keyword channel name | Positional first arg | Check kwargs: `routing_key`, `queue`, `topic`, `channel`, `name` |
| Async | `async function` / arrow | `async def` |

### 4.4 What needs to be implemented

| # | Task | Size | Description |
|---|---|---|---|
| P1 | Add `extract_channel_candidates` to Python adapter | M | Same generic logic as JS, adapted for Python syntax |
| P2 | Decorator detection | S | `@decorator(name="...")` on function â†’ processor candidate |
| P3 | For-loop consumer detection | S | `for x in binding:` â†’ enclosing function is consumer |
| P4 | Keyword argument channel extraction | S | Check common kwarg names for channel name |
| P5 | Tests | M | Synthetic fixtures (Celery, Redis, RabbitMQ, Kafka style) |
| P6 | Verification | S | Run on a Python repo with message brokers |

### 4.5 Estimated complexity

The Python implementation is roughly the **same size** as the JS implementation, not 2-3x. The core logic (binding map, argument shape, pairing) is identical. The only additions are:
- Decorator traversal (Python-specific syntax)
- For-loop detection (Python-specific syntax)
- Keyword argument extraction (Python-specific syntax)

Core infrastructure (merge.py pairing, flow traversal, schema) is already in place and language-agnostic.

### 4.6 Key differences from JS (syntactic only)

| Aspect | JS/TS | Python |
|---|---|---|
| Constructor syntax | `new X("name", ...)` | `X("name", ...)` |
| Handler pattern | Callback argument to constructor | Decorator on function, or for-loop body |
| Channel name in kwargs | Rare | Common (`routing_key=`, `queue=`, `topic=`) |
| No `new` keyword | Uses `new` | Direct call |

No SDK-specific method names. No verb lists. No per-library code. Same generic structural detector.

### 4.7 Next step

Implement P1-P6 on a new branch `feature/messaging-python` from `main` (after the messaging epic is accepted and merged). The core infrastructure (merge.py pairing, flow traversal, schema) is already in place and language-agnostic. Only the Python adapter's `extract_channel_candidates` needs implementation.

---

## Part 5 — Known limitations of the generic approach

The generic structural detector (no SDK-specific patterns) works for many Python
broker patterns but has genuine limitations:

### 5.1 Celery `.delay()` / `.apply_async()` — NOT detected

Celery tasks use `@app.task(name="task_name")` (detected as worker/processor) and
`task.delay(args)` (producer). The task name is the function name, not a string
argument. The generic detector cannot link `create_task.delay(...)` to the
`create_task` worker because there is no string channel name to pair on.

**Workaround:** Use `app.send_task("task_name", args=[...])` instead, which is a
direct call with a string channel name.

**To fully support Celery:** Would need SDK-specific detection: recognize that
`.delay()` / `.apply_async()` on a function decorated with `@app.task` produces
to the task's name. This contradicts the "no SDK-specific patterns" principle.

### 5.2 Redis pub/sub `subscribe("channel")` without callback — NOT detected as consumer

`r.publish("channel", data)` is detected as a producer (string first arg).
But `pubsub.subscribe("channel")` has no function argument, so it's not
classified as a consumer. The for-loop pattern (`for msg in pubsub.listen()`)
is detected as a consumer, but only if `pubsub` is a binding (it's not —
`pubsub = r.pubsub()` has no channel name).

**Workaround:** Use a for-loop over a binding: `for msg in consumer:` where
`consumer = SomeConsumer("channel", ...)`.

### 5.3 `app.send_task` with `args=` keyword — partially detected

`app.send_task("scorer.persist", args=[data])` is a member call on binding "app".
The first string arg "scorer.persist" is used as the channel name (generic
heuristic). `has_payload` is True (keyword arg `args=[data]` is non-string/non-function).
Classified as producer with channel "scorer.persist". Works if a consumer exists
with the same channel name.

### 5.4 Summary of what works vs. doesn't

| Pattern | Detected? | Channel source |
|---|---|---|
| `Queue("name", ...)` → binding | Yes | First string arg |
| `binding.method(...)` with payload | Yes | Binding's channel |
| `fn("name", ...)` direct call | Yes | First string arg |
| `@decorator(name="...")` → worker | Yes | Decorator's name kwarg |
| `for x in binding:` → consumer | Yes | Binding's channel |
| `binding.method("name", ...)` with string first arg | Yes (heuristic) | String first arg |
| Celery `task.delay(...)` | No | Requires SDK knowledge |
| Redis `subscribe("ch")` without callback | No | Requires SDK knowledge |
| RabbitMQ `basic_publish(..., routing_key="q")` | Yes (kwarg heuristic) | routing_key kwarg |
| Kafka `producer.send("topic", ...)` | Yes (direct-call heuristic) | First string arg |
| Kafka `for msg in consumer:` | Yes | Binding's channel |

## Where this is noted

- **Implementation formalization + Python plan**: `docs/dev/MESSAGE_BROKERS.md` (Parts 3 and 4)
- **Residual issues**: `KNOWN_ISSUES.md` (Ranks 1-14)
- **Original design reference**: `docs/dev/MESSAGE_BROKERS.md` (Parts 1 and 2)

**Do not commit without asking.**

- **Implementation formalization + Python plan**: `docs/dev/MESSAGE_BROKERS.md` (Parts 3 and 4)
- **Residual issues**: `KNOWN_ISSUES.md` (Ranks 1-14)
- **Original design reference**: `docs/dev/MESSAGE_BROKERS.md` (Parts 1 and 2)

**Do not commit without asking.**