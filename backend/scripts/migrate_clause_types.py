"""
One-shot migration: normalize free-string `clause_type` values into the
canonical ClauseType taxonomy across:
  - playbook_rules.clause_type
  - clause_library.clause_type
  - document_risks.clause_type

Uses raw asyncpg directly (NOT SQLAlchemy) so it works through Supabase's
transaction pooler (port 6543) without hitting the
`DuplicatePreparedStatementError` that bites multi-statement SQLAlchemy
sessions on a pgbouncer backend.

Usage:
    python scripts/migrate_clause_types.py             # dry-run
    python scripts/migrate_clause_types.py --apply     # write changes

Idempotent — re-running after a successful apply is a no-op.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import ssl as _ssl
import sys
from collections import Counter
from pathlib import Path
from typing import List, Tuple

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("migrate_clause_types")


def _bootstrap_imports() -> None:
    """Make `app.*` importable when the script is run directly from backend/."""
    here = Path(__file__).resolve()
    backend = here.parents[1]
    if str(backend) not in sys.path:
        sys.path.insert(0, str(backend))
    # Ensure config validation passes even if the runner doesn't have prod env.
    os.environ.setdefault("SECRET_KEY", "0" * 64)
    os.environ.setdefault(
        "ENCRYPTION_KEY", "tF1qXpJxXz8C6HfKVeXjK8sQvB0YcJZpYKQwLpHpRpA="
    )


_bootstrap_imports()

import asyncpg  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.services.clause_taxonomy import snap_to_clause_type  # noqa: E402


TABLES = ("playbook_rules", "clause_library", "document_risks")


def _ssl_ctx() -> _ssl.SSLContext:
    ctx = _ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = _ssl.CERT_NONE
    return ctx


async def _normalize_table(
    conn: asyncpg.Connection,
    table: str,
    apply: bool,
) -> Tuple[int, int, Counter, List[Tuple[str, str, str]]]:
    rows = await conn.fetch(f"SELECT id, clause_type FROM {table}")
    changed = 0
    dist: Counter = Counter()
    diffs: List[Tuple[str, str, str]] = []

    for r in rows:
        current = r["clause_type"]
        snapped = snap_to_clause_type(current).value
        dist[snapped] += 1
        if snapped != (current or ""):
            changed += 1
            diffs.append((r["id"], current, snapped))

    if apply and changed:
        for rid, _, new_value in diffs:
            await conn.execute(
                f"UPDATE {table} SET clause_type = $1 WHERE id = $2",
                new_value,
                rid,
            )

    return len(rows), changed, dist, diffs


async def main(apply: bool) -> None:
    mode = "APPLY" if apply else "DRY-RUN"
    logger.info("Mode: %s", mode)

    dsn = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
    conn = await asyncpg.connect(
        dsn,
        ssl=_ssl_ctx(),
        statement_cache_size=0,  # Required for Supabase transaction pooler
    )
    try:
        for table in TABLES:
            try:
                total, changed, dist, diffs = await _normalize_table(
                    conn, table, apply
                )
            except Exception as exc:
                logger.error("Failed on %s: %s", table, exc)
                continue

            verb = "would change" if not apply else "changed"
            logger.info("%s: %d/%d rows %s", table, changed, total, verb)
            if diffs:
                logger.info(
                    "%s: sample diffs (first 5): %s",
                    table,
                    [(str(r)[:8], o, n) for r, o, n in diffs[:5]],
                )
            top5 = dist.most_common(5)
            logger.info("%s: top types after migration: %s", table, top5)
    finally:
        await conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Write changes (default: dry-run)")
    args = parser.parse_args()
    asyncio.run(main(args.apply))
