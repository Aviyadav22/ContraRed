"""Regression tests for safe, versioned system-playbook upgrades."""

from types import SimpleNamespace

import pytest

from app.services import seed_defaults


class _Result:
    def __init__(self, *, one=None, rows=None):
        self._one = one
        self._rows = rows or []

    def fetchone(self):
        return self._one

    def fetchall(self):
        return self._rows


class _UpgradeSession:
    def __init__(self):
        self.statements = []
        self.commits = 0
        self.rollbacks = 0

    async def execute(self, statement, params=None):
        sql = str(statement)
        self.statements.append((sql, params or {}))
        if "SELECT id, version FROM playbooks" in sql:
            return _Result(
                one=SimpleNamespace(
                    id="aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
                    version=1,
                )
            )
        if "SELECT id, clause_type FROM playbook_rules" in sql:
            return _Result(
                rows=[
                    SimpleNamespace(
                        id="bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
                        clause_type="data_breach_notification",
                    ),
                    SimpleNamespace(
                        id="cccccccc-cccc-4ccc-8ccc-cccccccccccc",
                        clause_type="legacy_custom_control",
                    ),
                ]
            )
        return _Result()

    async def commit(self):
        self.commits += 1

    async def rollback(self):
        self.rollbacks += 1


@pytest.mark.asyncio
async def test_upgrade_preserves_rule_ids_and_does_not_delete_unknown_rules(
    monkeypatch,
):
    source = {
        "name": "Versioned default",
        "description": "Updated source",
        "category": "dpa",
        "party_side": "buyer",
        "version": 2,
        "rules": [{
            "id": "dddddddd-dddd-4ddd-8ddd-dddddddddddd",
            "clause_type": "data_breach_notification",
            "primary_position": "Updated position",
            "fallback_position": None,
            "risk_level": "red",
            "detection_patterns": {
                "match_type": "regex",
                "patterns": ["breach"],
            },
        }],
    }
    monkeypatch.setattr(seed_defaults, "_load_all_playbooks", lambda: [source])
    session = _UpgradeSession()

    changed = await seed_defaults.seed_default_playbooks(session)

    assert changed == 1
    assert session.commits == 1
    assert session.rollbacks == 0
    sql_text = "\n".join(statement for statement, _ in session.statements)
    assert "UPDATE playbooks" in sql_text
    assert "UPDATE playbook_rules" in sql_text
    assert "DELETE" not in sql_text.upper()
    rule_update = next(
        params
        for statement, params in session.statements
        if "UPDATE playbook_rules" in statement
    )
    assert rule_update["id"] == "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
