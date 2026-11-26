# Message Brokers and Async Channels — Complete Plan and Residual Issues

Date: 2026-11-26
Branch (planned): `feature/messaging` (from `main` after E4 merge)
Status: PLANNED — not started. No code changes yet.

This document is written before the commit and merge of `feature/verification`
so the design survives the merge and can be picked up later. It has two parts:

1. Every residual issue that remains after the JS/TS call-graph work, explained
   in full.
2. The plan for modelling message brokers and async channels, explained in full.

---

# Part 1 — Residual issues explained

## 1.1 Why we abstain on dynamic composition

Tree-sitter is syntax-only. For the following patterns there is no static
mapping from "binding" to "channel name" or from "call site" to "callee
definition", so emitting an edge would be a guess:

* `Object.assign(target, { method() {} })`
* object spreads (`{ ...computed }`)
* computed dynamic keys (`obj["m" + x]()` or `obj[key]()`)
* decorator-based dependency injection
* proxy / wrapper service objects (`new Proxy(...)`, `Proxy.create(...)`)

A wrong edge in a flow diagram actively misleads someone learning the
codebase, and the user's stated principle is that the graph must stay honest
rather than complete-at-all-costs. So these are recorded in `unresolved`
with reason `ambiguous_chain` and get no edge. This is a **recall**
limitation, not a correctness bug: the existing edges are never fabricated.

## 1.2 Local classes — what the issue is

"Local classes" are classes defined inside the analysed repository (as opposed
to imported from a package). The concern: if we detect `new X("name")`
where `X` is a *locally-defined* class, we cannot tell whether `X` is a broker
(`class EventBus`) or just a regular data class (`class Foo`). A local class
used as a broker in a single file, with no cross-file producer/consumer pair,
would be missed. That is a recall limitation. The pairing rule (Part 2 §3)
is what protects us: a local class only becomes a `channel` when the same name
is used on both a send side and a handler side, so a plain DTO constructor
never materialises. Local classes are excluded at first; the pairing rule can
relax this later.

## 1.3 Prisma

`.prisma` files are currently skipped — the Cricklo skip list records
`unsupported file extension '.prisma'`. Prisma models are therefore invisible,
and `prisma.user.findMany()` is only a chain call that our resolver might
catch. Why deferred: parsing the Prisma schema language needs a new
grammar/parser, and modelling data definitions (models, fields, relations) is
a different kind of node from control flow. It is out of scope for the control-
flow work.

## 1.4 DTOs, types and data models — why deferred

The user explicitly scoped the current work to logical/control-flow components:
"right now lets only trace logical components like routes, middlewares,
helpers, utils, services, etc etc." Types, interfaces, DTOs, Zod schemas,
Prisma models and class-validator decorators are **data**, not control flow.
They need new node kinds, new detection, and new view semantics. Keeping
scope on control flow first avoids diluting the call-graph work.

## 1.5 SCIP remains required

Cartog's `calls` edges come primarily from SCIP (268 `calls` edges in Cricklo
came from SCIP). SCIP uses the TypeScript/Python **language server**, which has
full type information: it resolves generics, overloaded methods, decorators,
type-only imports, and re-exports through complex paths. Tree-sitter is
syntax-only and cannot do any of that. Our static resolver only fills gaps for
a narrow shape (`A.B.C(...)` through imports/re-exports/object-literal
property initializers). If `scip-typescript` is absent or fails, the graph
keeps only `inferred` edges and is much sparser. SCIP is therefore a hard
dependency for full-quality output, not an optional accelerator.

## 1.6 Rank 4 — duplicate node ids

During graph assembly, when a symbol appears in multiple files or is
re-exported, `Graph.duplicate_node_ids` accumulates the id. After assembly
the graph deduplicates them in `graph.nodes`, so the on-disk `graph.json` has
unique ids and `cartog check` on that file exits `0`. But `validate_graph`
still reports the accumulated duplicates as errors, so `cartog analyze` exits
`1` on a valid run. It is a **reporting bug**, not a data bug. Why it remains:
it is orthogonal to call-graph work and is recorded as OPEN; the fix is to
clear or rebuild the accumulator once assembly finishes.

## 1.7 Rank 6 — Windows `python3` lookup

`scip-python` 0.6.6 has no interpreter option; Pyright discovers its
environment itself. On Windows, `%LOCALAPPDATA%\Microsoft\WindowsApps\python3.exe`
(Windows Store Python 3.11) precedes every other candidate on `PATH`. Cartog's
`--python` only prepends the chosen interpreter's directory to `PATH` and sets
`VIRTUAL_ENV`, but a venv whose `Scripts` directory contains `python.exe` but
no `python3.exe` is ignored. Even `--python C:\Python313\python.exe` produced
`click 8.1.7` symbols instead of `8.5.0`. Why it remains: the defect is in
`scip-python`/Pyright, not in cartog; cartog can only warn or stage a
`python3` alias in a cartog-controlled directory. Deferred as "idle unless it
becomes a support problem."

## 1.8 Rank 7 — `new X(...)` is not a call edge

`classify_occurrence()` handles `call` and `call_expression` AST nodes but not
`new_expression`. So `new Ky(...)` walks up to the enclosing declaration and
is classified `references`/`other`. The occurrence resolves to the constructor
symbol, so the graph gets a `references` edge, not a `calls` edge. Why it
remains: it is a separate classification fix; the current task focused on
verification and chain repair. Low–Medium severity.

## 1.9 Rank 2 — local closures remain unsolved

Arrow functions assigned to `const` (e.g. `throwIfTotalTimeoutReached` in ky)
are not emitted as symbols by `scip-typescript`, so calls to them have no
callee node. Tree-sitter could create a node for them, but SCIP will not give
an occurrence symbol to start from, and tree-sitter alone cannot tell which
closure is being called if names collide. Why it remains: it requires
`scip-typescript` to emit symbols for closures (upstream limitation) or a
purely tree-sitter call resolver (a larger project).

## 1.10 Python equivalents remain

The verifier and chain resolver are TypeScript/JavaScript first. Python has
analogous patterns: FastAPI `APIRouter` inclusion, class-based views,
decorator-injected dependencies, and `module.fn()` calls through re-exported
package objects. Why deferred: the user explicitly asked to finish the JS/TS
implementation before moving to Python.

## 1.11 `app.use` mount points and inline handlers (Rank 9)

On Cricklo, 11 of 85 routes have no serves edge: ten `app.use("/api/v1/...",
authRoutes)` mounts (the router is stored as a default import with
`names=['default']`, so the local alias never matches a symbol) and one
`GET /api/v1/health` with an inline arrow handler. Why it remains: this is a
different resolution problem — default-import alias resolution and inline
handler nodes — not the member-chain resolver. Recorded as a follow-up.

## 1.12 Why dynamic composition is abstained on (reiterated)

Tree-sitter is syntax-only. For `Object.assign`, spreads, computed dynamic
keys and decorator-based DI, there is no static mapping from binding to
channel name or from call site to callee definition. Emitting an edge would
be a guess, and a wrong edge in a flow diagram actively misleads someone
learning the codebase. Abstain and record in `unresolved`. This is a recall
limitation by design, consistent with the principle that the graph must stay
honest.

---

# Part 2 — Plan: message brokers and async channels

## 2.1 Goal

Make BullMQ-style producer → channel → processor → service traces visible in
`flow.html`, using a **generic** structural detector that also covers
RabbitMQ, Kafka, Redis pub/sub and SQS without per-SDK code. BullMQ is the
first test case, not a special case.

## 2.2 The problem in concrete terms

On Cricklo today:

* `scorerPersistQueue.add(...)` in the services is a leaf call — nothing links
  it to the worker that handles `"scorer-persist"`.
* `scorerPersistWorker` (a `new Worker("scorer-persist", async (job) => {...})`)
  is a disconnected island: no symbol node for the worker or its inline
  processor, no `starts` edge from `npm run worker`.
* `flow.html` shows two dead worker entry points with one node each.
* The channel name `"scorer-persist"` is never modelled.

## 2.3 Core idea: data, not verbs

The relationship is carried by **channel identity**, not method names. A method
called `add` tells us nothing; what matters is that the same channel name is
used on a *send side* (payload argument) and a *handler side* (callback
argument). This directly answers the concern "how do we differentiate a
developer's own `add` method from a broker's": we do not differentiate by
method name at all.

Discriminators, in order of strength:

1. **Binding → channel map.** A binding is a "channel client" when it is
   initialized from a constructor or factory whose first argument is a string
   name (`new Queue("scorer-persist", conn)`,
   `new Worker("scorer-persist", fn)`, `redis.createClient(...)`,
   `amqp.connect(...)`). The name becomes the channel identity and the binding
   is mapped to it. Built-ins (`new Set()`) and local classes are excluded at
   first; the pairing rule below can relax this later.
2. **Argument shape.** For calls whose receiver is *not* a channel binding:
   * producer-like when a string/constant argument is accompanied by a
     non-function payload argument;
   * consumer-like when a string/constant argument is accompanied by a function
     argument whose parameter is used inside the body.
3. **Pairing (the verdict).** A `channel` node is materialized **only** when
   the same name appears on both a producer-like site and a consumer-like site,
   ideally in different files. A lone `emitter.emit("tick")` with no subscriber,
   or a developer `notifier.send()` with no handler, produces nothing. This
   eliminates the false-positive risk that a verb list would have.

No SDK catalog, no verb list. The only SDK-specific knowledge is the generic
shape "constructor/factory returning a client whose first string arg is a
channel name", which is stable across brokers.

## 2.4 Schema changes (2.1.0 → 2.2.0)

New node kinds:

* `channel` — a named queue/topic/exchange/channel.
* `worker` — a long-running consumer process.
* `processor` — the callback that handles a message.

New edge kinds:

* `produces` — enclosing function → channel.
* `consumes` — channel → processor (flow direction, crosses the async boundary).

## 2.5 Detection (JS/TS adapter)

* `new_expression` with a callee imported from an external package and a string
  first argument → candidate channel binding (`binding → channel` map).
* `new Worker(name, fn)` → `worker` node + `processor` node for `fn` (which may
  be an inline arrow function with no symbol today; create the node from the
  AST), linked by `consumes`.
* Any call on a binding already mapped to a channel, with a payload argument →
  `produces` edge from the enclosing function to the channel.
* Direct-name calls (`publish("x", data)` / `subscribe("x", fn)`) classified by
  argument shape and paired by name.
* Channel names that are constants are resolved through the existing
  member-chain resolver from the call-graph task.
* Abstain on ambiguity, dynamic keys, spreads, `Object.assign`, and `new` on
  non-external (local) bindings. Record abstentions in `unresolved`.

## 2.6 Flow traversal

`trace_call_flow` follows `produces`/`consumes`/`starts`, so a route that
enqueues a job traces through the channel into the processor and its downstream
calls. Async hops are **default-on** in `flow.html` and badged so they can be
filtered out.

## 2.7 Package.json `starts` repair (deferred)

Repairing `starts` (resolving `tsx src/queues/index.ts` etc.) would fix all
dead entry points, but it has its own failure modes (shell chaining, env vars,
`nodemon`, TS-vs-dist paths). It is **not** a prerequisite for the queue model
because `consumes` already lets producer routes trace into worker processors.
It will be a separate small pass if wanted.

## 2.8 Tests (red first)

1. Synthetic BullMQ fixture: one queue, one producer, one worker with a
   processor, plus a decoy queue name with only a producer (must not
   materialize).
2. Object literal with methods `c` and `d` → picks `c` (reuses the ambiguity
   rule from the chain resolver).
3. Ambiguous re-export → no channel.
4. Consumer handler is an inline arrow → verify a `processor` node is created.
5. Real-repo check: all three Cricklo queues become channel nodes;
   `POST /score-update → … → scorerPersistQueue → processor` traces
   end-to-end; manual source check on two to three flows.

## 2.9 Verification and evidence

* Cricklo before/after: counts of channels, workers, processors, produces,
  consumes edges; flow depth for the scorer routes.
* Golden fingerprints: expected to be unchanged (click/flask/ky use no brokers).
* Update `KNOWN_ISSUES.md` (Rank 9 becomes a follow-up for `app.use`/inline
  handlers; add a rank for brokers once measured), `VERIFICATION.md`
  (messaging section).
* Re-measure the V5 call sample if any new inferred edges appear in
  click/flask/ky (expected: none).

## 2.10 Open questions (for the author)

1. Consumer handler: real `processor` node (recommended) or attach `consumes`
   to the enclosing file node? → **decided: `processor` node**.
2. Channel names that are constants we cannot resolve (env vars, config) —
   abstain, or attempt a weaker match? → **decided: abstain**.
3. Should `consumes` edges be followed in `flow.html` by default (recommended)
   or behind a toggle? → **decided: default on, filterable**.

## 2.11 Residuals (recorded, not in scope here)

* Dynamic composition (`Object.assign`, spreads, computed dynamic keys) → abstain.
* Local closures / arrow functions assigned to `const` → no graph node (Rank 2).
* `new X()` is still a `references` edge, not a `calls` edge (Rank 7).
* `app.use` mount points and inline handlers → 11 unresolved routes (Rank 9).
* Python equivalents → next phase (Rank 10).
* DTOs, types, data models, Prisma → deferred.
* SCIP remains required for typed callees; Rank 6 Windows `python3` lookup unchanged.
* Rank 4 duplicate node id check failure unchanged.
* `inferred` confidence — consumers that filter to `resolved` only will miss
  them; `flow.html` follows all.
* Measurement limits — V5 sample is still a 60-edge sample, not exhaustive.
* UTF-16 position mismatch risk — verifier abstains rather than wrongly demotes.
