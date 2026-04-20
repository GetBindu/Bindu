#!/usr/bin/env python3
r"""One-shot backfill script for the owner_did column.

Use this after deploying alembic revision 20260418_0001 (which adds the
nullable owner_did column) and BEFORE rolling out the Phase 2 enforcement
commits that filter reads/writes by owner. Rows predating the column
have ``owner_did IS NULL`` and will become inaccessible to authenticated
callers once enforcement lands; this script assigns them to a designated
owner DID so the transition is invisible.

Usage:

    python scripts/backfill_owner_did.py --owner-did did:bindu:legacy
    python scripts/backfill_owner_did.py --owner-did did:bindu:legacy --dry-run
    python scripts/backfill_owner_did.py --owner-did did:bindu:legacy \
        --database-url postgresql+asyncpg://user:pw@host/bindu  # pragma: allowlist secret
    python scripts/backfill_owner_did.py --owner-did did:bindu:legacy \
        --schema did_bindu_alice

``--schema`` targets a single DID-specific schema created by the
``create_bindu_tables_in_schema`` helper (alembic 20260119_0001). Run the
script once per existing schema. The global ``public`` schema is the
default.

Safety:
  * Only touches rows where owner_did IS NULL. Never overwrites an existing
    owner.
  * Runs inside a single transaction per table pair. On any error both
    updates roll back.
  * ``--dry-run`` reports the row counts that would be updated without
    committing.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from typing import Awaitable, Callable

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection, create_async_engine


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument(
        "--owner-did",
        required=True,
        help="DID string to assign to all NULL-owner rows.",
    )
    p.add_argument(
        "--database-url",
        default=None,
        help="SQLAlchemy async URL (e.g. postgresql+asyncpg://...). "
        "Defaults to app_settings.storage.postgres_url.",
    )
    p.add_argument(
        "--schema",
        default="public",
        help="Postgres schema to target. Defaults to 'public'. Use a "
        "DID-specific schema name for per-DID deployments.",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Report the counts that would be updated, then roll back.",
    )
    return p.parse_args()


async def _count_null(conn: AsyncConnection, schema: str, table: str) -> int:
    stmt = text(f'SELECT COUNT(*) FROM "{schema}"."{table}" WHERE owner_did IS NULL')
    result = await conn.execute(stmt)
    return int(result.scalar() or 0)


async def _update_null(
    conn: AsyncConnection, schema: str, table: str, owner_did: str
) -> int:
    stmt = text(
        f'UPDATE "{schema}"."{table}" SET owner_did = :owner WHERE owner_did IS NULL'
    )
    result = await conn.execute(stmt, {"owner": owner_did})
    return int(result.rowcount or 0)


async def _run(
    database_url: str,
    schema: str,
    owner_did: str,
    dry_run: bool,
) -> int:
    """Return a process exit code: 0 on success, non-zero on failure."""
    engine = create_async_engine(database_url, future=True)
    try:
        async with engine.begin() as conn:
            tasks_null = await _count_null(conn, schema, "tasks")
            contexts_null = await _count_null(conn, schema, "contexts")
            print(f"schema={schema} tasks.owner_did IS NULL: {tasks_null} rows")
            print(f"schema={schema} contexts.owner_did IS NULL: {contexts_null} rows")

            if dry_run:
                print("--dry-run: rolling back, no data changed.")
                # Exit the transaction via exception so it rolls back cleanly.
                raise _DryRunRollback()

            tasks_updated = await _update_null(conn, schema, "tasks", owner_did)
            contexts_updated = await _update_null(conn, schema, "contexts", owner_did)
            print(f"updated tasks: {tasks_updated}")
            print(f"updated contexts: {contexts_updated}")
    except _DryRunRollback:
        pass
    finally:
        await engine.dispose()
    return 0


class _DryRunRollback(Exception):
    """Used to roll back the outer transaction on --dry-run."""


def _resolve_database_url(explicit: str | None) -> str:
    if explicit:
        return explicit
    # Lazy import so --help works without a configured environment.
    from bindu.settings import app_settings

    url = app_settings.storage.postgres_url
    if not url:
        raise SystemExit(
            "No database URL provided. Pass --database-url or set "
            "STORAGE__POSTGRES_URL."
        )
    return url


def main(runner: Callable[..., Awaitable[int]] = _run) -> int:
    """CLI entry point. Returns a process exit code.

    ``runner`` is injectable for tests — defaults to the real ``_run``.
    """
    args = _parse_args()
    database_url = _resolve_database_url(args.database_url)
    return asyncio.run(
        runner(
            database_url=database_url,
            schema=args.schema,
            owner_did=args.owner_did,
            dry_run=args.dry_run,
        )
    )


if __name__ == "__main__":
    sys.exit(main())
