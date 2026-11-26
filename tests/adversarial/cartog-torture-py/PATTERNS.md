# Pattern catalog — cartog-torture-py

154 labeled patterns.

| ID | Marker | Expected | Description |
|---|---|---|---|
| ENTRY-MODULE | `samples/cartog-torture-py/cartog/__main__.py:1` | node:entrypoint, edge:starts | 01.""" |
| ENTRY-CLI | `samples/cartog-torture-py/cli/app.py:4` | node:entrypoint, edge:starts | 01. |
| CLI-ANALYZE-01 | `samples/cartog-torture-py/cli/app.py:22` | node:command, edge:serves | command -> service call |
| CLI-DYNAMIC | `samples/cartog-torture-py/cli/registry.py:1` | node:command, edge:serves | 01.""" |
| CALL-DOTTED-01 | `samples/cartog-torture-py/cli/shared.py:1` | node:function, edge:calls | dotted chain via re-export |
| NAMESPACE | `samples/cartog-torture-py/namespace_pkg/plugin_a.py:1` | node:file | 01.""" |
| NAMESPACE | `samples/cartog-torture-py/namespace_pkg/plugin_b.py:1` | node:file | 02.""" |
| STUB | `samples/cartog-torture-py/stubs/legacy.pyi:1` | node:file | 01.""" |
| FIXTURE-TINY | `samples/cartog-torture-py/tests/fixtures/tiny_repo/main.py:1` | node:file | 01.""" |
| OOP-CATALOG | `samples/cartog-torture-py/src/catalog/classes.py:1` | node:class, edge:overrides | 01.""" |
| DYN-CATALOG | `samples/cartog-torture-py/src/catalog/dynamic.py:1` | abstain | 01.""" |
| IMPORT-CATALOG | `samples/cartog-torture-py/src/catalog/imports.py:1` | abstain | 01.""" |
| CONFIG-ENV-01 | `samples/cartog-torture-py/src/config/env_channels.py:1` | abstain | env-var channel name (abstain) |
| CONFIG-FEATURE-01 | `samples/cartog-torture-py/src/config/feature_flags.py:1` | abstain | conditional command registration |
| API-PROFILE | `samples/cartog-torture-py/src/controllers/profile_controller.py:1` | abstain | 01.""" |
| API-SCORE_UPDATE | `samples/cartog-torture-py/src/controllers/score_update_controller.py:1` | abstain | 01.""" |
| API-USER | `samples/cartog-torture-py/src/controllers/user_controller.py:1` | abstain | 01.""" |
| DI-PARAMETER | `samples/cartog-torture-py/src/di/fastapi_depends.py:1` |  | 01.""" |
| DI-CONSTRUCTOR | `samples/cartog-torture-py/src/di/injector_container.py:1` |  | 01.""" |
| DYN-GETATTR-01 | `samples/cartog-torture-py/src/dynamic/getattr_calls.py:1` | abstain | getattr(obj,name)() (abstain) |
| DYN-METACLASS-01 | `samples/cartog-torture-py/src/dynamic/metaclass.py:1` | abstain | metaclass dispatch |
| DYN-PARTIAL-01 | `samples/cartog-torture-py/src/dynamic/partial.py:1` | abstain | functools.partial |
| EVENT-BLINKER | `samples/cartog-torture-py/src/events/blinker_signals.py:1` | node:function, edge:calls | 01.""" |
| EVENT-DJANGO | `samples/cartog-torture-py/src/events/django_signals.py:1` | node:function, edge:calls | 01.""" |
| EVENT-PYEE | `samples/cartog-torture-py/src/events/pyee_events.py:1` | node:function, edge:calls | 01.""" |
| MIDDLEWARE-ASGI-01 | `samples/cartog-torture-py/src/middleware/asgi_middleware.py:1` | node:middleware, edge:uses | ASGI middleware class |
| MIDDLEWARE-DJANGO-01 | `samples/cartog-torture-py/src/middleware/django_middleware.py:1` | node:middleware, edge:uses | Django middleware class |
| MIDDLEWARE-FASTAPI-01 | `samples/cartog-torture-py/src/middleware/fastapi_middleware.py:1` | node:middleware, edge:uses | @app.middleware |
| OOP-CBV-01 | `samples/cartog-torture-py/src/oop/class_based_views.py:1` | node:class, edge:overrides | class-based view dispatch |
| OOP-OVERRIDE-01 | `samples/cartog-torture-py/src/oop/derived.py:1` | node:class, edge:overrides | super().run override |
| OOP-DESCRIPTOR-01 | `samples/cartog-torture-py/src/oop/descriptors.py:1` | node:class, edge:overrides | descriptor |
| PLUGIN-ENTRYPOINTS-01 | `samples/cartog-torture-py/src/plugin/entry_points.py:1` | abstain | entry_points discovery |
| PLUGIN-IMPORTLIB-01 | `samples/cartog-torture-py/src/plugin/importlib_loader.py:1` | abstain | importlib.import_module (abstain) |
| MQ-AZURE | `samples/cartog-torture-py/src/queues/azure_service_bus.py:1` | node:channel, edge:produces | 01.""" |
| MQ-CELERY | `samples/cartog-torture-py/src/queues/celery_app.py:1` | node:channel, edge:produces | 01.""" |
| MQ-GCP | `samples/cartog-torture-py/src/queues/gcp_pubsub.py:1` | node:channel, edge:produces | 01.""" |
| MQ-KAFKA | `samples/cartog-torture-py/src/queues/kafka.py:1` | node:channel, edge:produces | 01.""" |
| MQ-MQTT | `samples/cartog-torture-py/src/queues/mqtt.py:1` | node:channel, edge:produces | 01.""" |
| MQ-NATS | `samples/cartog-torture-py/src/queues/nats.py:1` | node:channel, edge:produces | 01.""" |
| MQ-RABBITMQ | `samples/cartog-torture-py/src/queues/rabbitmq.py:1` | node:channel, edge:produces | 01.""" |
| MQ-REDIS | `samples/cartog-torture-py/src/queues/redis_pubsub.py:1` | node:channel, edge:produces | 01.""" |
| MQ-SQS | `samples/cartog-torture-py/src/queues/sqs.py:1` | node:channel, edge:produces | 01.""" |
| ROUTE-DJANGO | `samples/cartog-torture-py/src/routes/django_urls.py:1` | node:route, edge:serves | 01.""" |
| ROUTE-FASTAPI | `samples/cartog-torture-py/src/routes/fastapi_app.py:1` | node:route, edge:serves | 01.""" |
| ROUTE-FLASK | `samples/cartog-torture-py/src/routes/flask_app.py:1` | node:route, edge:serves | 01.""" |
| RPC-GRAPHQL | `samples/cartog-torture-py/src/rpc/graphql_resolvers.py:1` | node:function, edge:calls | 01.""" |
| RPC-GRPC | `samples/cartog-torture-py/src/rpc/grpc_stub.py:1` | node:function, edge:calls | 01.""" |
| RPC-REST | `samples/cartog-torture-py/src/rpc/service_http.py:1` | node:function, edge:calls | 01.""" |
| SCHED-APS | `samples/cartog-torture-py/src/scheduler/apscheduler.py:1` | node:function, edge:calls | 01.""" |
| SCHED-BG | `samples/cartog-torture-py/src/scheduler/background_tasks.py:1` | node:function, edge:calls | 01.""" |
| SCHED-BEAT | `samples/cartog-torture-py/src/scheduler/celery_beat.py:1` | node:function, edge:calls | 01.""" |
| API-S5 | `samples/cartog-torture-py/src/services/admin_service.py:22` | abstain | admin_service service call chain |
| DB-BATCH-01 | `samples/cartog-torture-py/src/services/batch_db_service.py:21` | node:function, edge:calls | batch_db_service service call chain |
| SCHED-BEAT-01 | `samples/cartog-torture-py/src/services/beat_job_service.py:21` | node:function, edge:calls | beat_job_service service call chain |
| SCHED-BG-01 | `samples/cartog-torture-py/src/services/bg_job_service.py:21` | node:function, edge:calls | bg_job_service service call chain |
| EVENT-BLINKER-01 | `samples/cartog-torture-py/src/services/blinker_event_service.py:21` | node:function, edge:calls | blinker_event_service service call chain |
| MQ-CELERY-02 | `samples/cartog-torture-py/src/services/celery_consumer_service.py:21` | node:channel, edge:produces | celery_consumer_service service call chain |
| MQ-CELERY-01 | `samples/cartog-torture-py/src/services/celery_producer_service.py:21` | node:channel, edge:produces | celery_producer_service service call chain |
| DI-CONSTRUCTOR-01 | `samples/cartog-torture-py/src/services/constructor_di_service.py:21` |  | constructor_di_service service call chain |
| SCHED-APS-01 | `samples/cartog-torture-py/src/services/cron_job_service.py:21` | node:function, edge:calls | cron_job_service service call chain |
| EVENT-DJANGO-01 | `samples/cartog-torture-py/src/services/django_event_service.py:21` | node:function, edge:calls | django_event_service service call chain |
| MQ-GCP-01 | `samples/cartog-torture-py/src/services/gpubsub_service.py:21` | node:channel, edge:produces | gpubsub_service service call chain |
| RPC-GRAPHQL-01 | `samples/cartog-torture-py/src/services/graphql_service.py:21` | node:function, edge:calls | graphql_service service call chain |
| RPC-GRPC-01 | `samples/cartog-torture-py/src/services/grpc_client_service.py:22` | node:function, edge:calls | grpc_client_service service call chain |
| API-S6 | `samples/cartog-torture-py/src/services/health_service.py:21` | abstain | health_service service call chain |
| SCHED-INTERVAL-01 | `samples/cartog-torture-py/src/services/interval_job_service.py:21` | node:function, edge:calls | interval_job_service service call chain |
| CACHE-INVALIDATE-01 | `samples/cartog-torture-py/src/services/invalidate_cache_service.py:21` | node:function, edge:calls | invalidate_cache_service service call chain |
| MQ-KAFKA-02 | `samples/cartog-torture-py/src/services/kafka_consumer_service.py:22` | node:channel, edge:produces | kafka_consumer_service service call chain |
| MQ-KAFKA-01 | `samples/cartog-torture-py/src/services/kafka_producer_service.py:21` | node:channel, edge:produces | kafka_producer_service service call chain |
| API-S1 | `samples/cartog-torture-py/src/services/match_service.py:24` | abstain | match_service service call chain |
| WS-MESSAGE-01 | `samples/cartog-torture-py/src/services/message_ws_service.py:21` | node:function, edge:calls | message_ws_service service call chain |
| MQ-MQTT-01 | `samples/cartog-torture-py/src/services/mqtt_service.py:21` | node:channel, edge:produces | mqtt_service service call chain |
| MQ-NATS-01 | `samples/cartog-torture-py/src/services/nats_service.py:21` | node:channel, edge:produces | nats_service service call chain |
| DB-ORM-01 | `samples/cartog-torture-py/src/services/orm_db_service.py:21` | node:function, edge:calls | orm_db_service service call chain |
| DI-PARAMETER-01 | `samples/cartog-torture-py/src/services/parameter_di_service.py:21` |  | parameter_di_service service call chain |
| API-S3 | `samples/cartog-torture-py/src/services/profile_service.py:22` | abstain | profile_service service call chain |
| EVENT-PYEE-01 | `samples/cartog-torture-py/src/services/pyee_event_service.py:21` | node:function, edge:calls | pyee_event_service service call chain |
| DB-QUERY-01 | `samples/cartog-torture-py/src/services/query_db_service.py:21` | node:function, edge:calls | query_db_service service call chain |
| MQ-RABBITMQ-02 | `samples/cartog-torture-py/src/services/rabbit_consumer_service.py:22` | node:channel, edge:produces | rabbit_consumer_service service call chain |
| MQ-RABBITMQ-01 | `samples/cartog-torture-py/src/services/rabbit_producer_service.py:21` | node:channel, edge:produces | rabbit_producer_service service call chain |
| CACHE-READ-01 | `samples/cartog-torture-py/src/services/read_cache_service.py:22` | node:function, edge:calls | read_cache_service service call chain |
| FILE-READ-01 | `samples/cartog-torture-py/src/services/read_file_service.py:21` | node:file | read_file_service service call chain |
| MQ-REDIS-01 | `samples/cartog-torture-py/src/services/redis_pub_service.py:21` | node:channel, edge:produces | redis_pub_service service call chain |
| MQ-REDIS-02 | `samples/cartog-torture-py/src/services/redis_sub_service.py:22` | node:channel, edge:produces | redis_sub_service service call chain |
| RPC-REST-01 | `samples/cartog-torture-py/src/services/rest_service.py:21` | node:function, edge:calls | rest_service service call chain |
| WS-ROOM-01 | `samples/cartog-torture-py/src/services/room_ws_service.py:21` | node:function, edge:calls | room_ws_service service call chain |
| MQ-AZURE-01 | `samples/cartog-torture-py/src/services/servicebus_service.py:21` | node:channel, edge:produces | servicebus_service service call chain |
| MQ-SQS-01 | `samples/cartog-torture-py/src/services/sqs_service.py:21` | node:channel, edge:produces | sqs_service service call chain |
| DB-TX-01 | `samples/cartog-torture-py/src/services/transaction_db_service.py:22` | node:function, edge:calls | transaction_db_service service call chain |
| CACHE-TTL-01 | `samples/cartog-torture-py/src/services/ttl_cache_service.py:21` | node:function, edge:calls | ttl_cache_service service call chain |
| FILE-UPLOAD-01 | `samples/cartog-torture-py/src/services/upload_file_service.py:21` | node:file | upload_file_service service call chain |
| API-S2 | `samples/cartog-torture-py/src/services/user_service.py:22` | abstain | user_service service call chain |
| TRAP-LOGGER-01 | `samples/cartog-torture-py/src/traps/builtins.py:1` | abstain | logger.info (builtin, not channel) |
| TRAP-LOCAL-CLASS-01 | `samples/cartog-torture-py/src/traps/local_queue.py:1` | abstain | local class used as broker |
| TRAP-USER-PUBLISH-01 | `samples/cartog-torture-py/src/traps/user_methods.py:1` | abstain | ordinary publish() no channel context |
| CACHE-UTIL | `samples/cartog-torture-py/src/utils/cache_util.py:1` | node:function, edge:calls | 01.""" |
| WS-ROOM | `samples/cartog-torture-py/src/websocket/channels_consumer.py:1` | node:function, edge:calls | 01.""" |
| CLI-BUILD | `samples/cartog-torture-py/cli/commands/build.py:1` | node:command, edge:serves | 01.""" |
| CLI-CHECK | `samples/cartog-torture-py/cli/commands/check.py:1` | node:command, edge:serves | 01.""" |
| CLI-DIGEST | `samples/cartog-torture-py/cli/commands/digest.py:1` | node:command, edge:serves | 01.""" |
| CLI-DOCTOR | `samples/cartog-torture-py/cli/commands/doctor.py:1` | node:command, edge:serves | 01.""" |
| CLI-FLOW | `samples/cartog-torture-py/cli/commands/flow.py:1` | node:command, edge:serves | 01.""" |
| CLI-MAP | `samples/cartog-torture-py/cli/commands/map.py:1` | node:command, edge:serves | 01.""" |
| CLI-PARSE | `samples/cartog-torture-py/cli/commands/parse.py:1` | node:command, edge:serves | 01.""" |
| CLI-QUERY | `samples/cartog-torture-py/cli/commands/query.py:1` | node:command, edge:serves | 01.""" |
| CLI-SCIP | `samples/cartog-torture-py/cli/commands/scip.py:1` | node:command, edge:serves | 01.""" |
| CLI-VIEW | `samples/cartog-torture-py/cli/commands/view.py:1` | node:command, edge:serves | 01.""" |
| CLI-S | `samples/cartog-torture-py/cli/services/analyze_service.py:22` | node:command, edge:serves | analyze-01 — analyze_service cli service call chain |
| CLI-S | `samples/cartog-torture-py/cli/services/build_service.py:21` | node:command, edge:serves | build-01 — build_service cli service call chain |
| CLI-S | `samples/cartog-torture-py/cli/services/check_service.py:21` | node:command, edge:serves | check-01 — check_service cli service call chain |
| CLI-S | `samples/cartog-torture-py/cli/services/digest_service.py:21` | node:command, edge:serves | digest-01 — digest_service cli service call chain |
| CLI-S | `samples/cartog-torture-py/cli/services/doctor_service.py:21` | node:command, edge:serves | doctor-01 — doctor_service cli service call chain |
| CLI-S | `samples/cartog-torture-py/cli/services/flow_service.py:22` | node:command, edge:serves | flow-01 — flow_service cli service call chain |
| CLI-S | `samples/cartog-torture-py/cli/services/map_service.py:21` | node:command, edge:serves | map-01 — map_service cli service call chain |
| CLI-S | `samples/cartog-torture-py/cli/services/parse_service.py:21` | node:command, edge:serves | parse-01 — parse_service cli service call chain |
| CLI-S | `samples/cartog-torture-py/cli/services/query_service.py:21` | node:command, edge:serves | query-01 — query_service cli service call chain |
| CLI-S | `samples/cartog-torture-py/cli/services/scip_service.py:21` | node:command, edge:serves | scip-01 — scip_service cli service call chain |
| CLI-S | `samples/cartog-torture-py/cli/services/view_service.py:21` | node:command, edge:serves | view-01 — view_service cli service call chain |
| CORE-CONFIG | `samples/cartog-torture-py/cartog/core/config.py:1` | node:function | 01.""" |
| CORE-DIAGNOSTICS | `samples/cartog-torture-py/cartog/core/diagnostics.py:1` | node:function | 01.""" |
| CORE-JSONC | `samples/cartog-torture-py/cartog/core/jsonc.py:1` | node:function | 01 |
| CALL-ARROW-01 | `samples/cartog-torture-py/cartog/core/jsonc.py:2` | node:function, edge:calls | lambda assigned to const-style |
| CORE-LIMITS | `samples/cartog-torture-py/cartog/core/limits.py:1` | node:function | 01 |
| REF-ISINSTANCE-01 | `samples/cartog-torture-py/cartog/core/limits.py:2` | node:function, edge:references | isinstance reference |
| OOP-CLASS | `samples/cartog-torture-py/cartog/core/model.py:1` | node:class, edge:overrides | 01.""" |
| CORE-OUTPUT | `samples/cartog-torture-py/cartog/core/output.py:1` | node:function | 01 |
| REF-TYPE-01 | `samples/cartog-torture-py/cartog/core/output.py:2` | node:function, edge:references | type annotation reference |
| CORE-PROC | `samples/cartog-torture-py/cartog/core/proc.py:1` | node:function | 01 |
| REF-EXCEPTION-01 | `samples/cartog-torture-py/cartog/core/proc.py:2` | node:function, edge:references | exception reference |
| CALL-PROMISE-01 | `samples/cartog-torture-py/cartog/core/proc.py:5` | node:function, edge:calls | async await chain |
| CORE-TEXT | `samples/cartog-torture-py/cartog/core/text.py:1` | node:function | 01 |
| CALL-CALLBACK-01 | `samples/cartog-torture-py/cartog/core/text.py:2` | node:function, edge:calls | callback passed as arg |
| CORE-TIMING | `samples/cartog-torture-py/cartog/core/timing.py:1` | node:function | 01 |
| CALL-GENERATOR-01 | `samples/cartog-torture-py/cartog/core/timing.py:2` | node:function, edge:calls | generator |
| CORE-TOOLCHAIN | `samples/cartog-torture-py/cartog/core/toolchain.py:1` | node:function | 01.""" |
| CALL-DOTTED | `samples/cartog-torture-py/cartog/graph/merge.py:1` | node:function, edge:calls | 01.""" |
| REF-TYPE | `samples/cartog-torture-py/cartog/graph/validate.py:1` | node:function, edge:references | 01.""" |
| EXPORT-BARREL | `samples/cartog-torture-py/cartog/graph/__init__.py:1` | node:file, edge:imports | 01.""" |
| OOP-ABSTRACT-01 | `samples/cartog-torture-py/cartog/parse/base.py:1` | node:class, edge:overrides | abstract base + subclasses |
| CALL-DOTTED-03 | `samples/cartog-torture-py/cartog/parse/js_adapter.py:1` | node:function, edge:calls | A.B.C() through alias |
| REF-INHERITANCE | `samples/cartog-torture-py/cartog/parse/python_adapter.py:1` | node:function, edge:references | 01.""" |
| CALL-ASYNC | `samples/cartog-torture-py/cartog/render/export_html.py:1` | node:function, edge:calls | 02.""" |
| REF-CALLBACK-01 | `samples/cartog-torture-py/cartog/render/export_json.py:1` | node:function, edge:references | callback reference |
| CALL-MEMBER | `samples/cartog-torture-py/cartog/render/export_mermaid.py:1` | node:function, edge:calls | 02.""" |
| CALL-MEMBER | `samples/cartog-torture-py/cartog/render/views.py:1` | node:function, edge:calls | 01.""" |
| CALL-DYNAMIC-IMPORT-01 | `samples/cartog-torture-py/cartog/scan/cache.py:1` | node:function, edge:calls | importlib.import_module (abstain) |
| REF-DECORATOR-01 | `samples/cartog-torture-py/cartog/scan/manifests.py:1` | node:function, edge:references | decorator reference |
| CALL-IMPORT-01 | `samples/cartog-torture-py/cartog/scan/walk.py:1` | node:function, edge:calls | imports edge via internal import |
| EXPORT-BARREL-07 | `samples/cartog-torture-py/cartog/scan/__init__.py:1` | node:file, edge:imports | scan barrel |
| CALL-ASYNC | `samples/cartog-torture-py/cartog/scip/runner.py:1` | node:function, edge:calls | 01.""" |
| FILE-GENERATED-01 | `samples/cartog-torture-py/cartog/scip/scip_pb2.py:1` | node:file | generated-style pb2 stub |
| CALL-PARTIAL-01 | `samples/cartog-torture-py/cartog/scip/static_calls.py:1` | node:function, edge:calls | functools.partial style |
| FILE-ASSET-02 | `samples/cartog-torture-py/cartog/render/view_assets/viewer.css:1` | node:file | CSS asset */ |
| FILE-ASSET-01 | `samples/cartog-torture-py/cartog/render/view_assets/viewer.js:1` | node:file | bundled viewer asset |
