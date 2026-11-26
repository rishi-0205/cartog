"""Generate the Python torture repo: catalog stubs + ~55 connected spines."""
from pathlib import Path

BASE = Path('samples/cartog-torture-py')
F = {}

def add(path, content):
    F[path] = content.lstrip('\n')

def svc(name, layer, imports, chain, pattern):
    fn = name.replace('-', '_').replace('/', '_')
    imp = '\n'.join(imports)
    calls = '\n'.join(f'    {c}' for c in chain)
    return f'''"""{layer.title()} layer for {name}.

Part of the '{pattern}' torture spine. Documents a realistic call path through
validation, logging, and the next architectural layer.
"""
{imp}
from cartog.core.diagnostics import get_logger

logger = get_logger(__name__)


async def {fn}(input: object = None) -> dict:
    """Execute the {name} workflow.

    Args:
        input: validated caller input.

    Returns:
        A deterministic status dictionary with the hops taken.
    """
    # PATTERN: {pattern} — {name} {layer} call chain
    hops: list[str] = []
    if input is None:
        logger.warning("{name}: empty input, using defaults")
    try:
{calls}
        hops.append("{fn}")
        logger.info("{{ 'name': '{name}', 'hops': len(hops) }}")
        return {{"ok": True, "hops": hops}}
    except Exception as exc:
        logger.error("{{ 'err': exc, 'name': '{name}' }}")
        return {{"ok": False, "hops": hops, "error": str(exc)}}
'''

# ============ ROOT ============
add('pyproject.toml', '''[project]
name = "cartog-torture-py"
version = "0.1.0"
description = "Adversarial conformance sample: every cartog node/edge kind plus ~55 connected spines."
requires-python = ">=3.11"
dependencies = [
  "typer==0.15.1", "click==8.1.8", "fastapi==0.115.6", "flask==3.1.0",
  "django==5.1.4", "celery==5.4.0", "redis==5.2.1", "pika==1.3.2",
  "kafka-python==2.0.2", "boto3==1.35.90", "blinker==1.9.0",
  "apscheduler==3.11.0", "sqlalchemy==2.0.36", "grpcio==1.70.0",
  "dependency-injector==4.42.0", "paho-mqtt==2.1.0", "nats-py==2.10.0"
]

[project.scripts]
cartog-torture-py = "cli.app:main"
ctp = "cli.app:main"
''')
add('docker-compose.yml', '''services:
  redis: { image: redis:7-alpine }
  rabbitmq: { image: rabbitmq:3-management }
  kafka: { image: bitnami/kafka }
  worker: { build: ., command: python -m cartog }
  web: { build: ., command: python src/routes/fastapi_app.py }
  scheduler: { build: ., command: python src/scheduler/apscheduler.py }
''')
add('.github/workflows/ci.yml', '''name: CI
on: [push, pull_request]
jobs:
  test: { runs-on: ubuntu-latest, steps: [{ uses: actions/checkout@v4 }, { run: pytest }] }
  lint: { runs-on: ubuntu-latest, steps: [{ uses: actions/checkout@v4 }, { run: ruff check . }] }
''')
add('subsystems.toml', '''[[subsystem]]
name = "CLI"
pattern = "cli/**"

[[subsystem]]
name = "Messaging"
pattern = "src/queues/**"
''')

# ============ CLI ============
add('cli/__init__.py', '''"""CLI package for the Python torture sample."""
from .app import main
''')
add('cli/app.py', '''"""Primary Typer CLI entrypoint — mirrors cartog's own command set.

Every command delegates to a service in cli/services/, which calls into the
cartog package. PATTERN: ENTRY-CLI-01.
"""
import typer
from cartog.core.diagnostics import get_logger

app = typer.Typer()
logger = get_logger(__name__)


@app.callback()
def callback() -> None:
    """Global CLI callback executed before every command."""
    logger.info("cli callback")


@app.command()
def analyze(out: str = "cartog-out") -> None:
    """Analyze a repository — CLI spine CLI-S-analyze."""
    # PATTERN: CLI-ANALYZE-01 — command -> service call
    from cli.services.analyze_service import analyze_service
    analyze_service(out)


def main() -> None:
    """Console-script entrypoint."""
    app()
''')
add('cli/commands/__init__.py', '"""CLI command package."""\n')
cli_cmds = {
 'flow': '''"""Flow command — Click group form. PATTERN: CLI-FLOW-01."""
import click
from cli.services.flow_service import flow_service

@click.group()
def cli(): pass

@cli.command()
@click.option("--out", default="cartog-out")
def flow(out):
    """Trace call flow through the graph."""
    flow_service(out)
''',
 'view': '''"""View command — Typer option form. PATTERN: CLI-VIEW-01."""
import typer
from cli.services.view_service import view_service
app = typer.Typer()

@app.command()
def view(out: str = typer.Option("cartog-out")):
    """Generate the interactive viewer."""
    view_service(out)
''',
 'digest': '''"""Digest command — Click alias form. PATTERN: CLI-DIGEST-01."""
import click
from cli.services.digest_service import digest_service

@click.command()
@click.option("--alias", "-d", is_flag=True)
def digest(alias):
    """Generate an LLM digest."""
    digest_service(alias)
''',
 'check': '''"""Check command — argparse dynamic dispatch. PATTERN: CLI-CHECK-01."""
import argparse
from cli.services.check_service import check_service

def build_parser():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers()
    c = sub.add_parser("check", func=check_service)
    c.set_defaults(func=check_service)
    return p

def run(argv=None):
    args = build_parser().parse_args(argv)
    args.func(args)
''',
 'parse': '''"""Parse command — typer sub-app. PATTERN: CLI-PARSE-01."""
import typer
from cli.services.parse_service import parse_service
sub = typer.Typer()

@sub.command()
def parse():
    """Run the parse stage."""
    parse_service()
''',
 'scip': '''"""SCIP command — typer. PATTERN: CLI-SCIP-01."""
import typer
from cli.services.scip_service import scip_service
app = typer.Typer()

@app.command()
def scip():
    """Run the SCIP indexer."""
    scip_service()
''',
 'build': '''"""Build command — dynamic registration. PATTERN: CLI-BUILD-01."""
import click
from cli.services.build_service import build_service

@click.group()
def build(): pass

for name in ["parse", "scip"]:
    build.add_command(click.Command(name, callback=lambda n=name: build_service(n)))
''',
 'map': '''"""Map command — cross-command invoke. PATTERN: CLI-MAP-01."""
import click
from cli.services.map_service import map_service

@click.command()
@click.pass_context
def map(ctx):
    """Map a repository."""
    map_service()
    ctx.invoke(other)

@click.command()
def other(): pass
''',
 'doctor': '''"""Doctor command — callback only. PATTERN: CLI-DOCTOR-01."""
import typer
app = typer.Typer()

@app.callback()
def doctor():
    """Check the environment."""
    from cli.services.doctor_service import doctor_service
    doctor_service()
''',
 'query': '''"""Query command — async handler. PATTERN: CLI-QUERY-01."""
import asyncio
from cli.services.query_service import query_service

def main():
    asyncio.run(query_service())
''',
}
for name, body in cli_cmds.items():
    add(f'cli/commands/{name}.py', body)
add('cli/registry.py', '''"""Command registry — dynamic registration loop. PATTERN: CLI-DYNAMIC-01."""
from cli.app import app

def register():
    for name in ["parse", "scip"]:
        app.command()(lambda n=name: None)
''')

# ============ CLI SERVICES (10 spines) ============
cli_svcs = {
 'analyze': (['from cartog.scip.runner import index_project', 'from cartog.graph.merge import build_graph'], ['    await index_project(out)', '    g = build_graph([])', '    logger.info(f"nodes={len(g.nodes)}")'], 'CLI-S-analyze-01', True),
 'flow': (['from cartog.render.views import trace_call_flow', 'from cartog.render.export_mermaid import export_mermaid'], ['    t = trace_call_flow(None)', '    export_mermaid(t)'], 'CLI-S-flow-01', True),
 'view': (['from cartog.render.export_html import export_html'], ['    html = await export_html()', '    logger.info(f"bytes={len(html)}")'], 'CLI-S-view-01', True),
 'check': (['from cartog.graph.validate import validate_graph'], ['    errors = validate_graph(None)', '    logger.info(f"errors={len(errors)}")'], 'CLI-S-check-01', False),
 'parse': (['from cartog.parse.python_adapter import PythonAdapter'], ['    adapter = PythonAdapter()', '    logger.info(adapter.name)'], 'CLI-S-parse-01', False),
 'scip': (['from cartog.scip.runner import index_project'], ['    await index_project("cartog-out")'], 'CLI-S-scip-01', True),
 'build': (['from cartog.graph.merge import build_graph'], ['    build_graph([])'], 'CLI-S-build-01', False),
 'map': (['from cartog.render.views import trace_call_flow'], ['    trace_call_flow(None)'], 'CLI-S-map-01', False),
 'doctor': (['from cartog.core.toolchain import check_toolchain'], ['    logger.info(str(check_toolchain()))'], 'CLI-S-doctor-01', False),
 'query': (['from cartog.render.views import generate_digest'], ['    generate_digest(None)'], 'CLI-S-query-01', True),
 'digest': (['from cartog.render.views import generate_digest'], ['    generate_digest(None)'], 'CLI-S-digest-01', False),
}
for name, (imports, calls, pattern, is_async) in cli_svcs.items():
    add(f'cli/services/{name}_service.py', svc(f'{name}_service', 'cli service', imports, calls, pattern))

# ============ CARTOG PACKAGE ============
add('cartog/__init__.py', '''"""Cartog-like package for the Python torture sample."""
__version__ = "0.1.0"
from cartog.core.model import Node
''')
add('cartog/__main__.py', '''"""python -m entrypoint. PATTERN: ENTRY-MODULE-01."""
from cli.app import main
main()
''')
add('cartog/core/__init__.py', '"""Core package."""\n')
add('cartog/core/diagnostics.py', '''"""Structured logging helper. PATTERN: CORE-DIAGNOSTICS-01."""
import logging

def get_logger(name: str):
    """Return a named logger."""
    return logging.getLogger(name)
''')
add('cartog/core/model.py', '''"""Core graph model — class, method, override, new-expression. PATTERN: OOP-CLASS-01."""
class Base:
    """Base class."""
    def make(self) -> str:
        """Base operation."""
        return "base"

class Node(Base):
    """Node subclass overriding make."""
    def make(self) -> str:
        """Override that calls super — emits overrides edge."""
        return super().make() + ":node"

node = Node()
''')
add('cartog/core/config.py', '''"""Configuration constants. PATTERN: CORE-CONFIG-01."""
OUT_DIR = "cartog-out"
MAX_FILE_SIZE_MB = 1
''')
add('cartog/core/toolchain.py', '''"""Toolchain checks. PATTERN: CORE-TOOLCHAIN-01."""
def check_toolchain() -> bool:
    """Return whether required tools are present."""
    return True
''')
add('cartog/graph/__init__.py', '''"""Graph package re-export. PATTERN: EXPORT-BARREL-01."""
from cartog.graph.merge import Graph
''')
add('cartog/graph/merge.py', '''"""Graph assembly — dotted chains via re-export. PATTERN: CALL-DOTTED-01."""
from cartog.graph import Graph

def build_graph(files: list) -> Graph:
    """Build a graph from parsed files."""
    return Graph.build().validate()
''')
add('cartog/graph/validate.py', '''"""Graph validation. PATTERN: REF-TYPE-01."""
def validate_graph(g: object) -> list[str]:
    """Return validation errors."""
    return []
''')
add('cartog/scip/__init__.py', '"""SCIP package."""\n')
add('cartog/scip/runner.py', '''"""SCIP runner — async/await chain. PATTERN: CALL-ASYNC-01."""
from cartog.graph.merge import build_graph

async def index_project(out: str) -> object:
    """Index a project with SCIP."""
    await decode()
    return build_graph([])

async def decode() -> None:
    """Decode the SCIP index."""
    return None
''')
add('cartog/render/__init__.py', '"""Render package."""\n')
add('cartog/render/views.py', '''"""View model + flow tracing. PATTERN: CALL-MEMBER-01."""
def trace_call_flow(g: object) -> list:
    """Trace the call flow from a graph."""
    return []

def generate_digest(g: object) -> str:
    """Generate an LLM digest."""
    return "# Digest"
''')
add('cartog/render/export_mermaid.py', '''"""Mermaid exporter. PATTERN: CALL-MEMBER-02."""
from cartog.render.views import trace_call_flow

def export_mermaid(g: object) -> str:
    """Export a Mermaid diagram."""
    trace_call_flow(g)
    return "graph TD"
''')
add('cartog/render/export_html.py', '''"""HTML exporter. PATTERN: CALL-ASYNC-02."""
async def export_html() -> str:
    """Export a self-contained map.html."""
    return "<html></html>"
''')
add('cartog/parse/__init__.py', '"""Parse package."""\n')
add('cartog/parse/python_adapter.py', '''"""Python adapter — inheritance. PATTERN: REF-INHERITANCE-01."""
from abc import ABC, abstractmethod

class Adapter(ABC):
    """Abstract adapter."""
    @abstractmethod
    def parse(self) -> None:
        """Parse source."""

class PythonAdapter(Adapter):
    """Concrete Python adapter."""
    def parse(self) -> None:
        """Parse Python source."""
        return None
''')

# ============ API ROUTE SPINES ============
add('src/routes/fastapi_app.py', '''"""FastAPI routes — API-S1, API-S2. PATTERN: ROUTE-FASTAPI-01."""
from fastapi import FastAPI, APIRouter, Depends
from src.controllers.score_update_controller import score_update_controller
from src.controllers.user_controller import user_controller

app = FastAPI()
router = APIRouter()

@app.post("/api/v1/match/score-update")
async def score_update(payload: dict, dep=Depends(provide)) -> dict:
    """Score update endpoint with DI dependency (must emit decorator ref)."""
    return await score_update_controller(payload)

@app.get("/api/v1/users")
async def users() -> dict:
    """List users endpoint."""
    return user_controller()

router.get("/api/v1/health")(health)
app.include_router(router)

def health() -> dict:
    """Health check."""
    return {"ok": True}

def provide() -> object:
    """DI provider."""
    return object()
''')
add('src/routes/flask_app.py', '''"""Flask blueprint routes — API-S3. PATTERN: ROUTE-FLASK-01."""
from flask import Flask, Blueprint
from src.controllers.profile_controller import profile_controller

app = Flask(__name__)
bp = Blueprint("profile", __name__)

@app.route("/api/v1/match", methods=["POST"])
def match_route():
    """Flask match route."""
    return profile_controller()

@bp.route("/api/v1/profile")
def profile_route():
    """Blueprint profile route."""
    return profile_controller()

app.register_blueprint(bp)
''')
add('src/routes/django_urls.py', '''"""Django URLconf + class-based view — API-S4. PATTERN: ROUTE-DJANGO-01."""
from django.urls import path
from django.views.generic import View

class MatchView(View):
    """Class-based view for match data."""
    def get(self, request):
        """Handle GET."""
        return None
    def dispatch_request(self):
        """Dispatch to the right method."""
        return self.get()

urlpatterns = [path("api/v1/match/", MatchView.as_view())]
''')
add('src/controllers/__init__.py', '"""Controllers package."""\n')
for name, target in [('score_update', 'match'), ('user', 'user'), ('profile', 'profile')]:
    add(f'src/controllers/{name}_controller.py', f'''"""Controller for {name} — API spine. PATTERN: API-{name.upper()}-01."""
from src.services.{target}_service import {target}_service

async def {name}_controller(payload: object = None) -> dict:
    """Delegate to the {target} service."""
    return await {target}_service(payload)
''')

# ============ SERVICE SPINES ============
svc_specs = {
 'match_service': (['from src.queues.celery_app import send_task', 'from src.queues.redis_pubsub import publish', 'from src.websocket.channels_consumer import broadcast', 'from src.repositories.match_repository import persist'], ['    send_task("score.persist", [data])', '    publish("notifications", data)', '    await broadcast("room", data)', '    return persist(data)'], 'API-S1', True),
 'user_service': (['from src.queues.redis_pubsub import publish', 'from src.repositories.user_repository import find'], ['    publish("user-events", data)', '    return find()'], 'API-S2', False),
 'profile_service': (['from src.queues.rabbitmq import basic_publish', 'from src.repositories.user_repository import find'], ['    basic_publish("q1", data)', '    return find()'], 'API-S3', False),
 'health_service': (['from src.utils.cache_util import cache_get'], ['    return cache_get("health")'], 'API-S6', False),
 'admin_service': (['from src.queues.kafka import send_kafka', 'from src.repositories.admin_repository import rebuild'], ['    await send_kafka("events", data)', '    return rebuild()'], 'API-S5', True),
 # MQ per method/broker
 'celery_producer_service': (['from src.queues.celery_app import send_task, delay_task, apply_async_task'], ['    send_task("score.persist", [data])', '    delay_task(data)', '    apply_async_task(data)'], 'MQ-CELERY-01', False),
 'celery_consumer_service': (['from src.repositories.match_repository import persist'], ['    return persist(data)'], 'MQ-CELERY-02', False),
 'redis_pub_service': (['from src.queues.redis_pubsub import publish'], ['    publish("notifications", data)'], 'MQ-REDIS-01', False),
 'redis_sub_service': (['from src.queues.redis_pubsub import subscribe', 'from src.repositories.event_repository import save'], ['    subscribe("notifications")', '    return save()'], 'MQ-REDIS-02', False),
 'rabbit_producer_service': (['from src.queues.rabbitmq import basic_publish'], ['    basic_publish("q1", data)'], 'MQ-RABBITMQ-01', False),
 'rabbit_consumer_service': (['from src.queues.rabbitmq import basic_consume', 'from src.repositories.match_repository import persist'], ['    basic_consume("q1", on_msg)', '    return persist(data)'], 'MQ-RABBITMQ-02', False),
 'kafka_producer_service': (['from src.queues.kafka import send_kafka'], ['    await send_kafka("events", data)'], 'MQ-KAFKA-01', True),
 'kafka_consumer_service': (['from src.queues.kafka import consume', 'from src.repositories.event_repository import save'], ['    for msg in consume("events"):', '        save(msg)', '    return None'], 'MQ-KAFKA-02', False),
 'sqs_service': (['from src.queues.sqs import send_sqs'], ['    send_sqs("body")'], 'MQ-SQS-01', False),
 'nats_service': (['from src.queues.nats import publish_nats'], ['    publish_nats("subject", data)'], 'MQ-NATS-01', False),
 'gpubsub_service': (['from src.queues.gcp_pubsub import publish_gcp'], ['    publish_gcp("topic", data)'], 'MQ-GCP-01', False),
 'servicebus_service': (['from src.queues.azure_service_bus import send_azure'], ['    send_azure("queue", data)'], 'MQ-AZURE-01', False),
 'mqtt_service': (['from src.queues.mqtt import publish_mqtt'], ['    publish_mqtt("topic", "payload")'], 'MQ-MQTT-01', False),
 # Scheduler
 'cron_job_service': (['from src.repositories.match_repository import rebuild'], ['    return rebuild()'], 'SCHED-APS-01', False),
 'beat_job_service': (['from src.queues.celery_app import send_task'], ['    send_task("score.persist", [data])'], 'SCHED-BEAT-01', False),
 'bg_job_service': (['from src.repositories.event_repository import save'], ['    return save()'], 'SCHED-BG-01', False),
 'interval_job_service': (['from src.utils.cache_util import cache_set'], ['    cache_set("ttl", 1)'], 'SCHED-INTERVAL-01', False),
 # Event
 'blinker_event_service': (['from src.events.blinker_signals import signal_send'], ['    signal_send("tick", data)'], 'EVENT-BLINKER-01', False),
 'django_event_service': (['from src.events.django_signals import django_send'], ['    django_send("signal", data)'], 'EVENT-DJANGO-01', False),
 'pyee_event_service': (['from src.events.pyee_events import emit'], ['    emit("tick", data)'], 'EVENT-PYEE-01', False),
 # RPC
 'grpc_client_service': (['from src.rpc.grpc_stub import call_grpc', 'from src.repositories.user_repository import find'], ['    call_grpc()', '    return find()'], 'RPC-GRPC-01', False),
 'graphql_service': (['from src.rpc.graphql_resolvers import resolve_user'], ['    return resolve_user()'], 'RPC-GRAPHQL-01', False),
 'rest_service': (['from src.rpc.service_http import fetch_service'], ['    return fetch_service("/users")'], 'RPC-REST-01', False),
 # DB
 'query_db_service': (['from src.repositories.match_repository import find'], ['    return find()'], 'DB-QUERY-01', False),
 'transaction_db_service': (['from src.utils.db_util import with_transaction', 'from src.repositories.match_repository import persist'], ['    return with_transaction(lambda: persist(data))'], 'DB-TX-01', False),
 'batch_db_service': (['from src.utils.db_util import batch_insert'], ['    return batch_insert([])'], 'DB-BATCH-01', False),
 'orm_db_service': (['from src.utils.orm_util import orm_find'], ['    return orm_find()'], 'DB-ORM-01', False),
 # Cache
 'read_cache_service': (['from src.utils.cache_util import cache_get, cache_set', 'from src.repositories.match_repository import find'], ['    v = cache_get("k")', '    if v is None:', '        cache_set("k", find())'], 'CACHE-READ-01', False),
 'invalidate_cache_service': (['from src.utils.cache_util import cache_del'], ['    cache_del("k")'], 'CACHE-INVALIDATE-01', False),
 'ttl_cache_service': (['from src.utils.cache_util import cache_expire'], ['    cache_expire("k", 60)'], 'CACHE-TTL-01', False),
 # WebSocket
 'room_ws_service': (['from src.websocket.channels_consumer import broadcast'], ['    await broadcast("room", data)'], 'WS-ROOM-01', True),
 'message_ws_service': (['from src.events.pyee_events import emit'], ['    emit("msg", data)'], 'WS-MESSAGE-01', False),
 # DI
 'constructor_di_service': (['from src.di.injector_container import container_get'], ['    return container_get("Service")'], 'DI-CONSTRUCTOR-01', False),
 'parameter_di_service': (['from src.di.fastapi_depends import provide'], ['    return provide()'], 'DI-PARAMETER-01', False),
 # File
 'read_file_service': (['from src.utils.file_util import read_config'], ['    return read_config("config.yaml")'], 'FILE-READ-01', False),
 'upload_file_service': (['from src.utils.s3_util import put_object'], ['    put_object("key", "body")'], 'FILE-UPLOAD-01', False),
}
for name, (imports, calls, pattern, is_async) in svc_specs.items():
    add(f'src/services/{name}.py', svc(name, 'service', imports, calls, pattern))

# ============ UTILS ============
add('src/utils/__init__.py', '"""Utilities package."""\n')
add('src/utils/cache_util.py', '''"""In-memory cache utility — cache spines. PATTERN: CACHE-UTIL-01."""
_store: dict[str, object] = {}

def cache_get(k: str) -> object:
    """Read a value from the cache."""
    return _store.get(k)

def cache_set(k: str, v: object) -> None:
    """Write a value to the cache."""
    _store[k] = v

def cache_del(k: str) -> None:
    """Invalidate a cache key."""
    _store.pop(k, None)

def cache_expire(k: str, ttl: int) -> None:
    """Set a TTL on a cache key."""
    _store[k] = ttl
''')
add('src/utils/db_util.py', '''"""Database utilities — transaction and batch spines."""
def with_transaction(fn):
    """Run a callable inside a transaction."""
    return fn()

def batch_insert(rows: list) -> int:
    """Insert a batch of rows."""
    return len(rows)
''')
add('src/utils/orm_util.py', '''"""ORM utility — ORM spine."""
def orm_find() -> list:
    """Find rows via the ORM."""
    return []
''')
add('src/utils/file_util.py', '''"""File read utility — file spines."""
from pathlib import Path

def read_config(path: str) -> str:
    """Read a config file."""
    return Path(path).read_text(encoding="utf-8")
''')
add('src/utils/s3_util.py', '''"""S3 upload utility — file storage spine."""
def put_object(key: str, body: str) -> None:
    """Upload an object to S3."""
    print(f"upload {key} {len(body)}")
''')

# ============ REPOSITORIES ============
add('src/repositories/__init__.py', '"""Repositories package."""\n')
repos = {
 'match_repository': ['find', 'find_by_id', 'persist', 'rebuild'],
 'user_repository': ['find', 'create'],
 'event_repository': ['save', 'list'],
 'admin_repository': ['rebuild'],
 'profile_repository': ['find'],
}
for name, methods in repos.items():
    lines = [f'"""Repository: {name}. Data-access layer for the spines."""', '']
    for m in methods:
        lines += [f'def {m}(*args: object) -> object:', f'    """{m.title()} operation."""', '    return args[0] if args else None', '', '']
    add(f'src/repositories/{name}.py', '\n'.join(lines))

# ============ QUEUES ============
queues = {
 'celery_app': '''"""Celery app — task decorator, send_task, delay, apply_async. PATTERN: MQ-CELERY-01."""
from celery import Celery, shared_task

app = Celery("torture")

@app.task(name="score.persist")
def persist(wrapper):
    """Persist a score event."""
    return None

@shared_task(name="score.rebuild")
def rebuild(wrapper):
    """Rebuild match stats."""
    return None

def send_task(name, args):
    """Send a task by name."""
    return app.send_task(name, args=args)

def delay_task(data):
    """Delay a task."""
    return persist.delay(data)

def apply_async_task(data):
    """Apply a task asynchronously."""
    return persist.apply_async(args=[data])
''',
 'redis_pubsub': '''"""Redis pub/sub — publish/subscribe methods. PATTERN: MQ-REDIS-01."""
import redis

r = redis.Redis()

def publish(ch: str, data: object) -> None:
    """Publish to a channel."""
    r.publish(ch, str(data))

def subscribe(ch: str) -> None:
    """Subscribe to a channel."""
    ps = r.pubsub()
    ps.subscribe(ch)
''',
 'rabbitmq': '''"""RabbitMQ/AMQP — basic_publish/basic_consume. PATTERN: MQ-RABBITMQ-01."""
import pika

connection = pika.BlockingConnection()
channel = connection.channel()

def basic_publish(queue: str, body: object) -> None:
    """Publish to a queue."""
    channel.basic_publish(exchange="", routing_key=queue, body=str(body))

def basic_consume(queue: str, cb) -> None:
    """Register a consumer callback."""
    channel.basic_consume(queue=queue, on_message_callback=cb)

def on_msg(ch, method, props, body):
    """Handle a consumed message."""
    return None
''',
 'kafka': '''"""Kafka — producer.send and consumer loop. PATTERN: MQ-KAFKA-01."""
from kafka import KafkaProducer, KafkaConsumer

producer = KafkaProducer()

async def send_kafka(topic: str, data: object) -> None:
    """Send to a Kafka topic."""
    producer.send(topic, value=str(data))

def consume(topic: str):
    """Iterate messages from a topic."""
    c = KafkaConsumer(topic)
    return c
''',
 'sqs': '''"""AWS SQS — send_message with QueueUrl kwarg. PATTERN: MQ-SQS-01."""
import boto3

sqs = boto3.client("sqs")

def send_sqs(body: str) -> None:
    """Send an SQS message."""
    sqs.send_message(QueueUrl="http://q", MessageBody=body)
''',
 'nats': '''"""NATS — publish to subject. PATTERN: MQ-NATS-01."""
def publish_nats(subject: str, data: object) -> None:
    """Publish to a NATS subject."""
    print(subject, data)
''',
 'gcp_pubsub': '''"""Google Pub/Sub — publish. PATTERN: MQ-GCP-01."""
def publish_gcp(topic: str, data: object) -> None:
    """Publish to a GCP topic."""
    print(topic, data)
''',
 'azure_service_bus': '''"""Azure Service Bus — send. PATTERN: MQ-AZURE-01."""
def send_azure(queue: str, data: object) -> None:
    """Send to an Azure queue."""
    print(queue, data)
''',
 'mqtt': '''"""MQTT — publish to topic. PATTERN: MQ-MQTT-01."""
def publish_mqtt(topic: str, payload: str) -> None:
    """Publish an MQTT message."""
    print(topic, payload)
''',
 'decoys': '''"""Decoys — producer-only queue and local Queue class must NOT materialize."""
from celery import Celery

app = Celery("t")

@app.task(name="orphan")
def orphan(x):
    """Producer-only task."""
    return None

app.send_task("orphan", args=[1])

class Queue:
    """Local class named Queue — must not become a channel."""
    def add(self, x):
        """Add an item."""
        return None

Queue().add(1)
''',
}
for name, content in queues.items():
    add(f'src/queues/{name}.py', content)

# ============ SCHEDULERS ============
add('src/scheduler/__init__.py', '"""Scheduler package."""\n')
add('src/scheduler/apscheduler.py', '''"""APScheduler — cron job spine. PATTERN: SCHED-APS-01."""
from apscheduler.schedulers.background import BackgroundScheduler
from src.repositories.match_repository import rebuild

scheduler = BackgroundScheduler()
scheduler.add_job(rebuild, "cron")
''')
add('src/scheduler/celery_beat.py', '''"""Celery Beat — string task name schedule. PATTERN: SCHED-BEAT-01."""
from celery import Celery

app = Celery("t")
app.conf.beat_schedule = {"x": {"task": "score.persist", "schedule": 1.0}}
''')
add('src/scheduler/background_tasks.py', '''"""FastAPI BackgroundTasks — add_task spine. PATTERN: SCHED-BG-01."""
from fastapi import BackgroundTasks

def notify(bt: BackgroundTasks) -> None:
    """Schedule a background task."""
    bt.add_task(send)

def send() -> None:
    """Send the notification."""
    return None
''')

# ============ EVENTS ============
add('src/events/__init__.py', '"""Events package."""\n')
add('src/events/blinker_signals.py', '''"""Blinker Signal — send/connect. PATTERN: EVENT-BLINKER-01."""
from blinker import Signal

sig = Signal("tick")

def recv(sender):
    """Handle a signal."""
    return None

sig.connect(recv)

def signal_send(name, data):
    """Send a signal."""
    sig.send("src")
''')
add('src/events/django_signals.py', '''"""Django signals — @receiver. PATTERN: EVENT-DJANGO-01."""
from django.dispatch import receiver, Signal

s = Signal()

@receiver(s)
def on_signal(sender, **kwargs):
    """Handle the signal."""
    return None

def django_send(name, data):
    """Send a Django signal."""
    s.send(sender=None)
''')
add('src/events/pyee_events.py', '''"""pyee EventEmitter — emit/on. PATTERN: EVENT-PYEE-01."""
from pyee import EventEmitter

e = EventEmitter()

def on_tick():
    """Handle the tick event."""
    return None

e.on("tick", on_tick)

def emit(name, data):
    """Emit an event."""
    e.emit(name, data)
''')

# ============ RPC ============
add('src/rpc/__init__.py', '"""RPC package."""\n')
add('src/rpc/grpc_stub.py', '''"""gRPC stub call. PATTERN: RPC-GRPC-01."""
import grpc

channel = grpc.insecure_channel("localhost:50051")

def call_grpc():
    """Call a gRPC method."""
    return channel
''')
add('src/rpc/graphql_resolvers.py', '''"""GraphQL resolver map. PATTERN: RPC-GRAPHQL-01."""
resolvers = {"Query": {"user": lambda: None}}

def resolve_user():
    """Resolve the user query."""
    return resolvers["Query"]["user"]()
''')
add('src/rpc/service_http.py', '''"""Inter-service REST call. PATTERN: RPC-REST-01."""
import httpx

def fetch_service(path: str):
    """Call another service."""
    return httpx.get(f"http://svc{path}")
''')

# ============ WEBSOCKET ============
add('src/websocket/__init__.py', '"""WebSocket package."""\n')
add('src/websocket/channels_consumer.py', '''"""Django Channels async consumer — broadcast spine. PATTERN: WS-ROOM-01."""
from channels.generic.websocket import AsyncWebsocketConsumer

class Consumer(AsyncWebsocketConsumer):
    """Async WebSocket consumer."""
    async def receive(self, text_data=None):
        """Handle an incoming message."""
        await self.send(text_data)

async def broadcast(room: str, data: object) -> None:
    """Broadcast to a room."""
    return None
''')

# ============ DI ============
add('src/di/__init__.py', '"""DI package."""\n')
add('src/di/fastapi_depends.py', '''"""FastAPI Depends — parameter injection. PATTERN: DI-PARAMETER-01."""
from fastapi import Depends

def provide() -> object:
    """Provide a dependency."""
    return object()

def endpoint(x=Depends(provide)):
    """Endpoint with DI parameter."""
    return x
''')
add('src/di/injector_container.py', '''"""dependency_injector — service locator. PATTERN: DI-CONSTRUCTOR-01."""
from dependency_injector import containers, providers

class Container(containers.DeclarativeContainer):
    """DI container."""
    service = providers.Factory(object)

def container_get(name: str) -> object:
    """Resolve a service from the container."""
    return Container.service()
''')

# ============ CATALOG STUBS ============
add('src/catalog/dynamic.py', '''"""Dynamic composition catalog — all must abstain. PATTERN: DYN-CATALOG-01."""
class C:
    """Class with a method."""
    def m(self):
        """Method."""
        return None

getattr(C(), "m")()

def gen():
    """Generator."""
    yield 1
''')
add('src/catalog/classes.py', '''"""OOP catalog — abstract, static, property, recursion. PATTERN: OOP-CATALOG-01."""
from abc import ABC, abstractmethod

class A(ABC):
    """Abstract class."""
    @abstractmethod
    def run(self):
        """Run."""

class B(A):
    """Concrete class."""
    @staticmethod
    def make():
        """Factory."""
        return B()
    @property
    def ok(self):
        """Property."""
        return True
    @ok.setter
    def ok(self, v):
        """Setter."""
        return None
    def run(self):
        """Override."""
        super().run()

def rec(n):
    """Recursion."""
    return rec(n - 1) if n > 0 else 0
''')
add('src/catalog/imports.py', '''"""Import/export catalog — re-exports, TYPE_CHECKING, dynamic. PATTERN: IMPORT-CATALOG-01."""
from src.catalog.classes import B as Renamed
from typing import TYPE_CHECKING
import importlib

if TYPE_CHECKING:
    from src.catalog.classes import A

def load(name):
    """Dynamic import — must be unresolved."""
    return importlib.import_module(name)
''')

# ============ NAMESPACE / STUBS / FIXTURES ============
add('namespace_pkg/plugin_a.py', '''"""PEP 420 namespace module A. PATTERN: NAMESPACE-01."""
def plugin():
    """Plugin entry."""
    return None
''')
add('namespace_pkg/plugin_b.py', '''"""PEP 420 namespace module B. PATTERN: NAMESPACE-02."""
def plugin():
    """Plugin entry."""
    return None
''')
add('stubs/legacy.pyi', '''"""Type stub file. PATTERN: STUB-01."""
def legacy(x: int) -> int: ...
''')
add('tests/fixtures/tiny_repo/pyproject.toml', '[project]\nname = "tiny-repo"\nversion = "1.0.0"\n')
add('tests/fixtures/tiny_repo/main.py', '''"""Nested fixture. PATTERN: FIXTURE-TINY-01."""
def tiny():
    """Tiny function."""
    return None
''')

for rel, content in F.items():
    p = BASE / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding='utf-8')

print(f'wrote {len(F)} files to {BASE}')
