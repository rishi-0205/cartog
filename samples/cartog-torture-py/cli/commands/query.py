"""Query command — async handler. PATTERN: CLI-QUERY-01."""
import asyncio
from cli.services.query_service import query_service

def main():
    asyncio.run(query_service())
