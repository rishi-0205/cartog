# Adversarial Torture Samples — Final Findings

Date: 2026-11-26
Branch: `test/adversarial-samples`

## What was built

| Repo | Files | PATTERN markers | Purpose |
|---|---|---|---|
| `samples/cartog-torture-js` | 124 | 121 | JS/TS catalog + ~55 connected spines |
| `samples/cartog-torture-py` | 142 | 154 | Python catalog + ~55 connected spines |
| `samples/click` | 2 | 0 | Minimal compat stub for legacy reconciliation test |

Old samples (flask, ky, webscrapper, fastapi-celery) deleted. `samples.lock` and
`fetch_samples.py` updated to generate-only mode (no network clone).

**Quality standard met:** every file has a module docstring, function docstrings,
inline `PATTERN:` comments, 10–30 line bodies with validation/logging, real
cross-file/cross-folder/in-file calls, controller → service → util → repository
→ sink chains.

## Coverage

Both repos include every method variant:
- MQ producers: add/addBulk/send/publish/send_task/delay/apply_async/emit/enqueue/send_message/basic_publish/push
- MQ consumers: on/once/subscribe/consume/basic_consume/listen/receive/get/poll/eachMessage/ack/nack/retry
- Brokers: BullMQ, RabbitMQ, Kafka, Redis, SQS, Celery, NATS, GCP Pub/Sub, Azure Service Bus, MQTT
- Python decorators: CLI/route/task/DI/OOP/factory/stacked/class/async — all expected to emit `references` + `ref_kind: decorator`
- Components: databases (6 variants), caches (5), websockets (3), RPC (4), schedulers (5), events (4), DI (3), file/storage (3)

## Graph sizes

| Repo | no-scip | with SCIP |
|---|---|---|
| JS | 431 nodes / 175 edges | 431 / 384 |
| Python | 496 nodes / 237 edges | 496 / 566 |

## Connectivity results (real flow graphs, not just presence)

| Repo | no-scip | with SCIP |
|---|---|---|
| JS | 0/15 spines | 6/15 |
| Python | 0/15 | 5/15 (main CLI + API spines fully connected) |

Fully connected with SCIP: `flow`, `view`, `score_update`, `analyze` (Python);
`resolveUser`, and 5 more (JS). Each traced spine has 18–26 hops reaching
15–22 nodes through calls, produces, consumes, serves edges.

## Gaps exposed

1. **No-SCIP has no `calls` edges** — cartog cannot trace flow without the SCIP indexer. This is fundamental (documented in MESSAGE_BROKERS.md Part 1.5).
2. **JS CLI `command` nodes = 0** — commander/yargs commands produce function nodes but no `command`/`serves`. Still not fixed.
3. **Python decorator `ref_kind` now emitted** — SCIP run shows decorator references in graph (39 references with ref_kinds).
4. **MQ producer-only channels correctly excluded** — pairing rule works; only 1–3 channels materialized per repo despite dozens of queue declarations.
5. **Cross-file call chains work** with SCIP — controller → service → util → repository → sink traced end-to-end (score_update spine: 26 hops, 22 nodes).
6. **Several spines show 0 hops** because SCIP cannot resolve external-package calls (e.g. `boto3.client().send_message`, `httpx.get`) — expected limitation.

## 8. Verification

- Full suite: **290 passed, 4 skipped, 10 xfailed, 1 warning** (`docs/evidence/ADVERSARIAL-TESTS.txt`)
- Adversarial-only: **36 passed, 10 xfailed**
- Tests replace manual flow/node checking — they assert catalog coverage,
  real SCIP flow connectivity, decorator detection, MQ pairing, and
  deterministic graphs on every PR/Push.
- Evidence: `CONFORMANCE-*.txt`, `CONNECTIVITY-*.txt`, `ADVERSARIAL-TESTS.txt`

## Files (all uncommitted)

- `docs/ADVERSARIAL_SAMPLES.md` (plan)
- `docs/ADVERSARIAL_SAMPLES_FINDINGS.md` (this file)
- `docs/evidence/CONFORMANCE-*.txt`, `CONNECTIVITY-*.txt` (8 files)
- `scripts/gen_torture_js.py`, `gen_torture_py.py`, `gen_torture_groundtruth.py`,
  `gen_compat_stubs.py`, `fetch_samples.py`, `samples.lock`,
  `check_conformance.py`, `check_spine_connectivity.py`
- `tests/adversarial/` (expected.json + PATTERNS.md ×2)
- Plus earlier uncommitted: `cartog/parse/python_adapter.py`, `docs/dev/MESSAGE_BROKERS.md`
