# Pattern catalog — cartog-torture-js

121 labeled patterns.

| ID | Marker | Expected | Description |
|---|---|---|---|
| FIXTURE-TINY-01 | `samples/cartog-torture-js/tests/fixtures/tiny-repo/index.ts:1` | node:file | nested fixture file |
| EXPORT-BARREL-02 | `samples/cartog-torture-js/src/cli/index.ts:1` | node:file, edge:imports | cli barrel |
| CLI-HOOK-01 | `samples/cartog-torture-js/src/cli/middleware.ts:1` | node:command, edge:serves | preAction hook middleware |
| CLI-DYNAMIC-01 | `samples/cartog-torture-js/src/cli/registry.ts:7` | node:command, edge:serves | dynamic registration in loop |
| CLI-DIRECTORY-01 | `samples/cartog-torture-js/src/cli/registry.ts:9` | node:command, edge:serves | command loading from directory |
| CALL-DOTTED-01 | `samples/cartog-torture-js/src/cli/shared.ts:1` | node:function, edge:calls | dotted chain A.B.C() via import |
| CONFIG-FEATURE-01 | `samples/cartog-torture-js/src/config/feature-flags.ts:1` | abstain | conditional command registration |
| API-S1 | `samples/cartog-torture-js/src/controllers/scoreUpdate.controller.ts:4` | abstain | controller → service call |
| CALL-RECURSION-01 | `samples/cartog-torture-js/src/core/base-decl.ts:1` | node:function, edge:calls | recursive and mutual recursion |
| CALL-ARROW-01 | `samples/cartog-torture-js/src/core/jsonc.ts:1` | node:function, edge:calls | arrow function assigned to const |
| CALL-BIND-01 | `samples/cartog-torture-js/src/core/jsonc.ts:3` | node:function, edge:calls | .bind()/.call()/.apply() |
| REF-ISINSTANCE-01 | `samples/cartog-torture-js/src/core/limits.ts:1` | node:function, edge:references | isinstance-style type check reference |
| CALL-NEW-01 | `samples/cartog-torture-js/src/core/model.ts:10` | node:function, edge:calls | new X() constructor (references, not calls) |
| CALL-CALLBACK-01 | `samples/cartog-torture-js/src/core/text.ts:1` | node:function, edge:calls | callback passed as arg |
| CALL-GENERATOR-01 | `samples/cartog-torture-js/src/core/timing.ts:1` | node:function, edge:calls | generator / async generator |
| DYN-ASSIGN-01 | `samples/cartog-torture-js/src/dynamic/assign.ts:1` | abstain | Object.assign (abstain) |
| DYN-COMPUTED-01 | `samples/cartog-torture-js/src/dynamic/computed.ts:1` | abstain | computed dynamic keys (abstain) |
| DYN-PROXY-01 | `samples/cartog-torture-js/src/dynamic/proxy.ts:1` | abstain | Proxy / Reflect (abstain) |
| DYN-SPREAD-01 | `samples/cartog-torture-js/src/dynamic/spreads.ts:1` | abstain | object spread (abstain) |
| EVENT-DYNAMIC-01 | `samples/cartog-torture-js/src/events/signals.ts:1` | node:function, edge:calls | dynamic event name (abstain) |
| EXPORT-BARREL-03 | `samples/cartog-torture-js/src/graph/index.ts:1` | node:file, edge:imports | graph re-export barrel |
| CALL-DOTTED-02 | `samples/cartog-torture-js/src/graph/merge.ts:4` | node:function, edge:calls | A.B.C() through re-export |
| REF-TYPE-01 | `samples/cartog-torture-js/src/graph/validate.ts:3` | node:function, edge:references | type-annotation reference |
| MIDDLEWARE-CHAIN-01 | `samples/cartog-torture-js/src/middleware/chain.ts:1` | node:middleware, edge:uses | middleware chain uses edges |
| MIDDLEWARE-ERROR-02 | `samples/cartog-torture-js/src/middleware/error.ts:1` | node:middleware, edge:uses | error middleware form |
| OOP-ABSTRACT-02 | `samples/cartog-torture-js/src/oop/abstract.ts:1` | node:class, edge:overrides | abstract class |
| OOP-BASE-01 | `samples/cartog-torture-js/src/oop/base.ts:1` | node:class, edge:overrides | base class |
| OOP-OVERRIDE-01 | `samples/cartog-torture-js/src/oop/derived.ts:1` | node:class, edge:overrides | super.method override edge |
| OOP-MIXIN-01 | `samples/cartog-torture-js/src/oop/mixins.ts:1` | node:class, edge:overrides | mixin composition |
| OOP-ABSTRACT-01 | `samples/cartog-torture-js/src/parse/base.ts:1` | node:class, edge:overrides | abstract class + subclasses |
| EXPORT-BARREL-04 | `samples/cartog-torture-js/src/parse/index.ts:1` | node:file, edge:imports | parse barrel |
| CALL-CHAIN-REEXPORT-01 | `samples/cartog-torture-js/src/parse/js-adapter.ts:1` | node:function, edge:calls | A.B.C() through import alias |
| REF-INHERITANCE-01 | `samples/cartog-torture-js/src/parse/ts-adapter.ts:1` | node:function, edge:references | inheritance reference |
| PLUGIN-DIRECTORY-01 | `samples/cartog-torture-js/src/plugin/directory.ts:1` | abstain | load plugins from directory |
| PLUGIN-DYNAMIC-REQUIRE-01 | `samples/cartog-torture-js/src/plugin/loader.ts:1` | abstain | require(variable) (abstain) |
| REF-CALLBACK-01 | `samples/cartog-torture-js/src/render/export-json.ts:1` | node:function, edge:references | callback reference |
| CALL-MEMBER-01 | `samples/cartog-torture-js/src/render/views.ts:3` | node:function, edge:calls | member call chain |
| ENTRY-COMMONJS-01 | `samples/cartog-torture-js/src/routes/commonjs-entry.ts:1` | node:entrypoint, edge:starts | require.main === module |
| ROUTE-MOUNT-01 | `samples/cartog-torture-js/src/routes/express-app.ts:10` | node:route, edge:serves | app.use default import (Rank 9) |
| ROUTE-INLINE-01 | `samples/cartog-torture-js/src/routes/express-app.ts:14` | node:route, edge:serves | inline arrow handler (Rank 9) |
| RPC-GRPC-STUB-01 | `samples/cartog-torture-js/src/rpc/grpc-stub.ts:1` | node:function, edge:calls | generated-style stub |
| CALL-DYNAMIC-IMPORT-01 | `samples/cartog-torture-js/src/scan/cache.ts:1` | node:function, edge:calls | dynamic import(var) (abstain) |
| REF-DECORATOR-01 | `samples/cartog-torture-js/src/scan/manifests.ts:1` | node:function, edge:references | decorator reference |
| CALL-IMPORT-01 | `samples/cartog-torture-js/src/scan/walk.ts:1` | node:function, edge:calls | imports edge via internal import |
| FILE-GENERATED-01 | `samples/cartog-torture-js/src/scip/proto.ts:1` | node:file | generated-style protobuf stub |
| CALL-ASYNC-01 | `samples/cartog-torture-js/src/scip/runner.ts:4` | node:function, edge:calls | async/await chain |
| CALL-PARTIAL-01 | `samples/cartog-torture-js/src/scip/static-calls.ts:1` | node:function, edge:calls | bound/partial-style call |
| API-S5 | `samples/cartog-torture-js/src/services/admin.service.ts:17` | abstain | admin.service service call chain |
| SCHED-AGENDA-01 | `samples/cartog-torture-js/src/services/agenda.job.service.ts:16` | node:function, edge:calls | agenda.job.service service call chain |
| DB-BATCH-01 | `samples/cartog-torture-js/src/services/batch.db.service.ts:16` | node:function, edge:calls | batch.db.service service call chain |
| MQ-BULLMQ-01 | `samples/cartog-torture-js/src/services/bullmq.producer.service.ts:16` | node:channel, edge:produces | bullmq.producer.service service call chain |
| MQ-BULLMQ-02 | `samples/cartog-torture-js/src/services/bullmq.worker.service.ts:17` | node:channel, edge:produces | bullmq.worker.service service call chain |
| DI-CONSTRUCTOR-01 | `samples/cartog-torture-js/src/services/constructor.di.service.ts:16` |  | constructor.di.service service call chain |
| SCHED-CRON-01 | `samples/cartog-torture-js/src/services/cron.job.service.ts:16` | node:function, edge:calls | cron.job.service service call chain |
| DI-DECORATOR-01 | `samples/cartog-torture-js/src/services/decorator.di.service.ts:16` |  | decorator.di.service service call chain |
| EVENT-EMIT-01 | `samples/cartog-torture-js/src/services/emit.event.service.ts:16` | node:function, edge:calls | emit.event.service service call chain |
| MQ-GCP-01 | `samples/cartog-torture-js/src/services/gpubsub.service.ts:16` | node:channel, edge:produces | gpubsub.service service call chain |
| RPC-GRAPHQL-01 | `samples/cartog-torture-js/src/services/graphql.service.ts:16` | node:function, edge:calls | graphql.service service call chain |
| RPC-GRPC-01 | `samples/cartog-torture-js/src/services/grpc.client.service.ts:17` | node:function, edge:calls | grpc.client.service service call chain |
| API-S6 | `samples/cartog-torture-js/src/services/health.service.ts:16` | abstain | health.service service call chain |
| CACHE-INVALIDATE-01 | `samples/cartog-torture-js/src/services/invalidate.cache.service.ts:16` | node:function, edge:calls | invalidate.cache.service service call chain |
| MQ-KAFKA-02 | `samples/cartog-torture-js/src/services/kafka.consumer.service.ts:17` | node:channel, edge:produces | kafka.consumer.service service call chain |
| MQ-KAFKA-01 | `samples/cartog-torture-js/src/services/kafka.producer.service.ts:16` | node:channel, edge:produces | kafka.producer.service service call chain |
| API-S1 | `samples/cartog-torture-js/src/services/match.service.ts:19` | abstain | match.service service call chain |
| WS-MESSAGE-01 | `samples/cartog-torture-js/src/services/message.ws.service.ts:17` | node:function, edge:calls | message.ws.service service call chain |
| MQ-MQTT-01 | `samples/cartog-torture-js/src/services/mqtt.service.ts:16` | node:channel, edge:produces | mqtt.service service call chain |
| EVENT-NAMED-01 | `samples/cartog-torture-js/src/services/named.event.service.ts:16` | node:function, edge:calls | named.event.service service call chain |
| MQ-NATS-01 | `samples/cartog-torture-js/src/services/nats.service.ts:16` | node:channel, edge:produces | nats.service service call chain |
| EVENT-ONCE-01 | `samples/cartog-torture-js/src/services/once.event.service.ts:16` | node:function, edge:calls | once.event.service service call chain |
| DB-ORM-01 | `samples/cartog-torture-js/src/services/orm.db.service.ts:16` | node:function, edge:calls | orm.db.service service call chain |
| DB-QUERY-01 | `samples/cartog-torture-js/src/services/query.db.service.ts:16` | node:function, edge:calls | query.db.service service call chain |
| MQ-RABBITMQ-02 | `samples/cartog-torture-js/src/services/rabbitmq.consumer.service.ts:17` | node:channel, edge:produces | rabbitmq.consumer.service service call chain |
| MQ-RABBITMQ-01 | `samples/cartog-torture-js/src/services/rabbitmq.producer.service.ts:16` | node:channel, edge:produces | rabbitmq.producer.service service call chain |
| CACHE-READ-01 | `samples/cartog-torture-js/src/services/read.cache.service.ts:17` | node:function, edge:calls | read.cache.service service call chain |
| FILE-READ-01 | `samples/cartog-torture-js/src/services/read.file.service.ts:16` | node:file | read.file.service service call chain |
| MQ-REDIS-01 | `samples/cartog-torture-js/src/services/redis.pubsub.service.ts:16` | node:channel, edge:produces | redis.pubsub.service service call chain |
| SCHED-REPEAT-01 | `samples/cartog-torture-js/src/services/repeat.job.service.ts:16` | node:function, edge:calls | repeat.job.service service call chain |
| RPC-REST-01 | `samples/cartog-torture-js/src/services/rest.service.ts:16` | node:function, edge:calls | rest.service service call chain |
| WS-ROOM-01 | `samples/cartog-torture-js/src/services/room.ws.service.ts:16` | node:function, edge:calls | room.ws.service service call chain |
| MQ-AZURE-01 | `samples/cartog-torture-js/src/services/servicebus.service.ts:16` | node:channel, edge:produces | servicebus.service service call chain |
| MQ-SQS-01 | `samples/cartog-torture-js/src/services/sqs.service.ts:16` | node:channel, edge:produces | sqs.service service call chain |
| SCHED-TIMER-01 | `samples/cartog-torture-js/src/services/timer.job.service.ts:16` | node:function, edge:calls | timer.job.service service call chain |
| DB-TX-01 | `samples/cartog-torture-js/src/services/transaction.db.service.ts:17` | node:function, edge:calls | transaction.db.service service call chain |
| RPC-TRPC-01 | `samples/cartog-torture-js/src/services/trpc.service.ts:16` | node:function, edge:calls | trpc.service service call chain |
| CACHE-TTL-01 | `samples/cartog-torture-js/src/services/ttl.cache.service.ts:16` | node:function, edge:calls | ttl.cache.service service call chain |
| FILE-UPLOAD-01 | `samples/cartog-torture-js/src/services/upload.file.service.ts:16` | node:file | upload.file.service service call chain |
| API-S2 | `samples/cartog-torture-js/src/services/user.service.ts:17` | abstain | user.service service call chain |
| TRAP-ARRAY-ADD-01 | `samples/cartog-torture-js/src/traps/builtins.ts:1` | abstain | array.add (builtin, not channel) |
| TRAP-LOCAL-CLASS-01 | `samples/cartog-torture-js/src/traps/local-queue.ts:1` | abstain | local class used as broker |
| TRAP-USER-PUBLISH-01 | `samples/cartog-torture-js/src/traps/user-methods.ts:1` | abstain | ordinary publish() with no channel context |
| ROUTE-NEXT-NESTED-01 | `samples/cartog-torture-js/src/routes/next-app/users/route.ts:1` | node:route, edge:serves | nested app router |
| FILE-ASSET-02 | `samples/cartog-torture-js/src/render/view-assets/viewer.css:1` | node:file | bundled CSS asset */ |
| FILE-ASSET-01 | `samples/cartog-torture-js/src/render/view-assets/viewer.js:1` | node:file | bundled viewer asset |
| CLI-ANALYZE | `samples/cartog-torture-js/src/cli/commands/analyze.command.ts:2` | node:command, edge:serves | 01 |
| CLI-ANALYZE-02 | `samples/cartog-torture-js/src/cli/commands/analyze.command.ts:10` | node:command, edge:serves | command → service call |
| CLI-BUILD | `samples/cartog-torture-js/src/cli/commands/build.command.ts:2` | node:command, edge:serves | 01 |
| CLI-BUILD-02 | `samples/cartog-torture-js/src/cli/commands/build.command.ts:10` | node:command, edge:serves | command → service call |
| CLI-CHECK | `samples/cartog-torture-js/src/cli/commands/check.command.ts:2` | node:command, edge:serves | 01 |
| CLI-CHECK-02 | `samples/cartog-torture-js/src/cli/commands/check.command.ts:10` | node:command, edge:serves | command → service call |
| CLI-DIGEST | `samples/cartog-torture-js/src/cli/commands/digest.command.ts:2` | node:command, edge:serves | 01 |
| CLI-DIGEST-02 | `samples/cartog-torture-js/src/cli/commands/digest.command.ts:10` | node:command, edge:serves | command → service call |
| CLI-DOCTOR | `samples/cartog-torture-js/src/cli/commands/doctor.command.ts:2` | node:command, edge:serves | 01 |
| CLI-DOCTOR-02 | `samples/cartog-torture-js/src/cli/commands/doctor.command.ts:10` | node:command, edge:serves | command → service call |
| CLI-FLOW | `samples/cartog-torture-js/src/cli/commands/flow.command.ts:2` | node:command, edge:serves | 01 |
| CLI-FLOW-02 | `samples/cartog-torture-js/src/cli/commands/flow.command.ts:10` | node:command, edge:serves | command → service call |
| CLI-MAP | `samples/cartog-torture-js/src/cli/commands/map.command.ts:2` | node:command, edge:serves | 01 |
| CLI-MAP-02 | `samples/cartog-torture-js/src/cli/commands/map.command.ts:10` | node:command, edge:serves | command → service call |
| CLI-PARSE | `samples/cartog-torture-js/src/cli/commands/parse.command.ts:2` | node:command, edge:serves | 01 |
| CLI-PARSE-02 | `samples/cartog-torture-js/src/cli/commands/parse.command.ts:10` | node:command, edge:serves | command → service call |
| CLI-QUERY | `samples/cartog-torture-js/src/cli/commands/query.command.ts:2` | node:command, edge:serves | 01 |
| CLI-QUERY-02 | `samples/cartog-torture-js/src/cli/commands/query.command.ts:10` | node:command, edge:serves | command → service call |
| CLI-SCIP | `samples/cartog-torture-js/src/cli/commands/scip.command.ts:2` | node:command, edge:serves | 01 |
| CLI-SCIP-02 | `samples/cartog-torture-js/src/cli/commands/scip.command.ts:10` | node:command, edge:serves | command → service call |
| CLI-VIEW | `samples/cartog-torture-js/src/cli/commands/view.command.ts:2` | node:command, edge:serves | 01 |
| CLI-VIEW-02 | `samples/cartog-torture-js/src/cli/commands/view.command.ts:10` | node:command, edge:serves | command → service call |
| CLI-S-ANALYZE-01 | `samples/cartog-torture-js/src/cli/services/analyze.service.ts:17` | node:command, edge:serves | analyze cli service call chain |
| CLI-S-CHECK-01 | `samples/cartog-torture-js/src/cli/services/check.service.ts:17` | node:command, edge:serves | check cli service call chain |
| CLI-S-DOCTOR-01 | `samples/cartog-torture-js/src/cli/services/doctor.service.ts:17` | node:command, edge:serves | doctor cli service call chain |
| CLI-S-FLOW-01 | `samples/cartog-torture-js/src/cli/services/flow.service.ts:17` | node:command, edge:serves | flow cli service call chain |
| CLI-S-MAP-01 | `samples/cartog-torture-js/src/cli/services/map.service.ts:17` | node:command, edge:serves | map cli service call chain |
| CLI-S-VIEW-01 | `samples/cartog-torture-js/src/cli/services/view.service.ts:17` | node:command, edge:serves | view cli service call chain |
