"""
Playbook Version Control Service — Phase 6 ContraRed.

Provides snapshot-on-mutation, version history, field-level diff, and
rollback for Playbook objects stored in PostgreSQL via SQLAlchemy async.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.playbook import (
    Playbook,
    PlaybookCondition,
    PlaybookRule,
    PlaybookRuleDependency,
    PlaybookRuleOverride,
    PlaybookRuleTier,
    PlaybookVersion,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Serialisation helpers
# ---------------------------------------------------------------------------

def _ser(value: Any) -> Any:
    """Recursively convert non-JSON-serialisable values to primitives."""
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {k: _ser(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_ser(i) for i in value]
    return value


def _serialize_tier(tier: PlaybookRuleTier) -> Dict[str, Any]:
    return {
        "id": str(tier.id),
        "tier_level": tier.tier_level,
        "position_text": tier.position_text,
        "guidance_notes": tier.guidance_notes,
        "risk_level_at_tier": tier.risk_level_at_tier,
    }


def _serialize_override(override: PlaybookRuleOverride) -> Dict[str, Any]:
    return {
        "id": str(override.id),
        "condition_id": str(override.condition_id),
        "rule_id": str(override.rule_id),
        "override_risk_level": override.override_risk_level,
        "override_position_text": override.override_position_text,
        "override_is_deal_breaker": override.override_is_deal_breaker,
        "override_tier_level": override.override_tier_level,
        "suppress_rule": override.suppress_rule,
        "notes": override.notes,
    }


def _serialize_rule(rule: PlaybookRule) -> Dict[str, Any]:
    return {
        "id": str(rule.id),
        "clause_type": rule.clause_type,
        "primary_position": rule.primary_position,
        "fallback_position": rule.fallback_position,
        "risk_level": rule.risk_level.value if hasattr(rule.risk_level, "value") else rule.risk_level,
        "is_deal_breaker": rule.is_deal_breaker,
        "detection_patterns": _ser(rule.detection_patterns),
        "suggested_language": _ser(rule.suggested_language),
        "order_index": rule.order_index,
        "requires_ai_verification": rule.requires_ai_verification,
        "verification_prompt": rule.verification_prompt,
        "jurisdiction_overrides": _ser(rule.jurisdiction_overrides),
        "priority": rule.priority,
        "category": rule.category,
        "subcategory": rule.subcategory,
        "tags": _ser(rule.tags),
        "tiers": [_serialize_tier(t) for t in (rule.tiers or [])],
    }


def _serialize_condition(cond: PlaybookCondition) -> Dict[str, Any]:
    return {
        "id": str(cond.id),
        "name": cond.name,
        "description": cond.description,
        "condition_type": cond.condition_type,
        "operator": cond.operator,
        "condition_value": _ser(cond.condition_value),
        "is_active": cond.is_active,
        "priority": cond.priority,
        "rule_overrides": [_serialize_override(o) for o in (cond.rule_overrides or [])],
    }


def _serialize_dependency(dep: PlaybookRuleDependency) -> Dict[str, Any]:
    return {
        "id": str(dep.id),
        "source_rule_id": str(dep.source_rule_id),
        "target_rule_id": str(dep.target_rule_id),
        "trigger_condition": dep.trigger_condition,
        "effect": dep.effect,
        "effect_params": _ser(dep.effect_params),
        "is_active": dep.is_active,
    }


def _build_snapshot(
    playbook: Playbook,
    conditions: List[PlaybookCondition],
    dependencies: List[PlaybookRuleDependency],
) -> Dict[str, Any]:
    """Produce a complete JSON-serialisable snapshot of the playbook."""
    return {
        "playbook": {
            "id": str(playbook.id),
            "name": playbook.name,
            "description": playbook.description,
            "category": playbook.category.value if hasattr(playbook.category, "value") else playbook.category,
            "is_public": playbook.is_public,
            "is_default": playbook.is_default,
            "version": playbook.version,
        },
        "rules": [_serialize_rule(r) for r in (playbook.rules_list or [])],
        "conditions": [_serialize_condition(c) for c in conditions],
        "dependencies": [_serialize_dependency(d) for d in dependencies],
    }


# ---------------------------------------------------------------------------
# Diff helpers
# ---------------------------------------------------------------------------

def _diff_rule(old: Dict[str, Any], new: Dict[str, Any]) -> Dict[str, Any]:
    """Return field-level changes between two rule snapshots (excluding tiers list)."""
    SKIP = {"tiers"}
    changes: Dict[str, Any] = {}
    all_keys = set(old) | set(new)
    for key in all_keys:
        if key in SKIP:
            continue
        old_val = old.get(key)
        new_val = new.get(key)
        if old_val != new_val:
            changes[key] = {"from": old_val, "to": new_val}

    # Tier-level diff
    old_tiers = {t["tier_level"]: t for t in old.get("tiers", [])}
    new_tiers = {t["tier_level"]: t for t in new.get("tiers", [])}
    tier_changes: Dict[str, Any] = {}
    for level in set(old_tiers) | set(new_tiers):
        if level not in old_tiers:
            tier_changes[str(level)] = {"added": new_tiers[level]}
        elif level not in new_tiers:
            tier_changes[str(level)] = {"removed": old_tiers[level]}
        elif old_tiers[level] != new_tiers[level]:
            tier_field_diff: Dict[str, Any] = {}
            for fk in set(old_tiers[level]) | set(new_tiers[level]):
                if old_tiers[level].get(fk) != new_tiers[level].get(fk):
                    tier_field_diff[fk] = {
                        "from": old_tiers[level].get(fk),
                        "to": new_tiers[level].get(fk),
                    }
            if tier_field_diff:
                tier_changes[str(level)] = tier_field_diff
    if tier_changes:
        changes["tiers"] = tier_changes

    return changes


# ---------------------------------------------------------------------------
# Service class
# ---------------------------------------------------------------------------

class PlaybookVersioningService:
    """Async service for playbook snapshot, history, diff, and rollback."""

    # ------------------------------------------------------------------
    # Internal load helpers
    # ------------------------------------------------------------------

    async def _load_playbook(self, db: AsyncSession, playbook_id: UUID) -> Playbook:
        """Load playbook with rules → tiers eagerly joined."""
        stmt = (
            select(Playbook)
            .where(Playbook.id == playbook_id)
            .options(
                selectinload(Playbook.rules_list).selectinload(PlaybookRule.tiers),
                selectinload(Playbook.rules_list).selectinload(PlaybookRule.overrides),
            )
        )
        result = await db.execute(stmt)
        playbook = result.scalar_one_or_none()
        if playbook is None:
            raise ValueError(f"Playbook {playbook_id} not found")
        return playbook

    async def _load_conditions(
        self, db: AsyncSession, playbook_id: UUID
    ) -> List[PlaybookCondition]:
        stmt = (
            select(PlaybookCondition)
            .where(PlaybookCondition.playbook_id == playbook_id)
            .options(selectinload(PlaybookCondition.rule_overrides))
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def _load_dependencies(
        self, db: AsyncSession, playbook_id: UUID
    ) -> List[PlaybookRuleDependency]:
        stmt = select(PlaybookRuleDependency).where(
            PlaybookRuleDependency.playbook_id == playbook_id
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def _next_version_number(
        self, db: AsyncSession, playbook_id: UUID
    ) -> int:
        stmt = select(func.coalesce(func.max(PlaybookVersion.version_number), 0)).where(
            PlaybookVersion.playbook_id == playbook_id
        )
        result = await db.execute(stmt)
        current_max: int = result.scalar_one()
        return current_max + 1

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def create_snapshot(
        self,
        db: AsyncSession,
        playbook_id: UUID,
        change_summary: str,
        user_id: UUID,
    ) -> PlaybookVersion:
        """
        Capture a full snapshot of the playbook in its current state and
        persist it as a new PlaybookVersion row.

        Returns the newly created PlaybookVersion instance.
        """
        logger.info(
            "Creating snapshot for playbook %s by user %s", playbook_id, user_id
        )

        playbook = await self._load_playbook(db, playbook_id)
        conditions = await self._load_conditions(db, playbook_id)
        dependencies = await self._load_dependencies(db, playbook_id)

        snapshot = _build_snapshot(playbook, conditions, dependencies)
        version_number = await self._next_version_number(db, playbook_id)

        version = PlaybookVersion(
            id=uuid.uuid4(),
            playbook_id=playbook_id,
            version_number=version_number,
            snapshot=snapshot,
            change_summary=change_summary,
            created_by=user_id,
            created_at=datetime.now(timezone.utc),
        )
        db.add(version)
        await db.commit()
        await db.refresh(version)

        logger.info(
            "Snapshot v%d created for playbook %s (version_id=%s)",
            version_number,
            playbook_id,
            version.id,
        )
        return version

    async def get_versions(
        self,
        db: AsyncSession,
        playbook_id: UUID,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        Return the version history for a playbook, most recent first.

        Each entry contains: id, version_number, change_summary, created_at,
        created_by.
        """
        stmt = (
            select(PlaybookVersion)
            .where(PlaybookVersion.playbook_id == playbook_id)
            .order_by(PlaybookVersion.version_number.desc())
            .limit(limit)
        )
        result = await db.execute(stmt)
        versions = result.scalars().all()

        return [
            {
                "id": str(v.id),
                "version_number": v.version_number,
                "change_summary": v.change_summary,
                "created_at": v.created_at.isoformat() if v.created_at else None,
                "created_by": str(v.created_by) if v.created_by else None,
            }
            for v in versions
        ]

    async def get_version(
        self,
        db: AsyncSession,
        version_id: UUID,
    ) -> Dict[str, Any]:
        """
        Return the full snapshot dict for the specified version.

        Raises ValueError when the version does not exist.
        """
        stmt = select(PlaybookVersion).where(PlaybookVersion.id == version_id)
        result = await db.execute(stmt)
        version = result.scalar_one_or_none()
        if version is None:
            raise ValueError(f"PlaybookVersion {version_id} not found")

        return {
            "id": str(version.id),
            "playbook_id": str(version.playbook_id),
            "version_number": version.version_number,
            "change_summary": version.change_summary,
            "created_at": version.created_at.isoformat() if version.created_at else None,
            "created_by": str(version.created_by) if version.created_by else None,
            "snapshot": version.snapshot,
        }

    async def diff_versions(
        self,
        db: AsyncSession,
        version_a_id: UUID,
        version_b_id: UUID,
    ) -> Dict[str, Any]:
        """
        Compare two playbook version snapshots and return a structured diff.

        version_a is treated as the "before" state and version_b as "after".

        Returned dict keys:
            rules_added         — rules present in b but not in a
            rules_removed       — rules present in a but not in b
            rules_modified      — rules present in both with field-level changes
            conditions_added    — conditions present in b but not in a
            conditions_removed  — conditions present in a but not in b
            dependencies_added  — dependencies present in b but not in a
            dependencies_removed— dependencies present in a but not in b
        """
        logger.info(
            "Diffing versions %s (before) vs %s (after)", version_a_id, version_b_id
        )

        ver_a = await self.get_version(db, version_a_id)
        ver_b = await self.get_version(db, version_b_id)

        snap_a: Dict[str, Any] = ver_a["snapshot"]
        snap_b: Dict[str, Any] = ver_b["snapshot"]

        # --- Rules ---
        rules_a: Dict[str, Dict] = {r["id"]: r for r in snap_a.get("rules", [])}
        rules_b: Dict[str, Dict] = {r["id"]: r for r in snap_b.get("rules", [])}

        rules_added = [rules_b[rid] for rid in rules_b if rid not in rules_a]
        rules_removed = [rules_a[rid] for rid in rules_a if rid not in rules_b]
        rules_modified: List[Dict[str, Any]] = []
        for rid in rules_a:
            if rid in rules_b:
                changes = _diff_rule(rules_a[rid], rules_b[rid])
                if changes:
                    rules_modified.append({
                        "id": rid,
                        "clause_type": rules_b[rid].get("clause_type"),
                        "changes": changes,
                    })

        # --- Conditions ---
        conds_a: Dict[str, Dict] = {c["id"]: c for c in snap_a.get("conditions", [])}
        conds_b: Dict[str, Dict] = {c["id"]: c for c in snap_b.get("conditions", [])}

        conditions_added = [conds_b[cid] for cid in conds_b if cid not in conds_a]
        conditions_removed = [conds_a[cid] for cid in conds_a if cid not in conds_b]

        # --- Dependencies ---
        deps_a: Dict[str, Dict] = {d["id"]: d for d in snap_a.get("dependencies", [])}
        deps_b: Dict[str, Dict] = {d["id"]: d for d in snap_b.get("dependencies", [])}

        dependencies_added = [deps_b[did] for did in deps_b if did not in deps_a]
        dependencies_removed = [deps_a[did] for did in deps_a if did not in deps_b]

        return {
            "version_a": {"id": str(version_a_id), "number": ver_a["version_number"]},
            "version_b": {"id": str(version_b_id), "number": ver_b["version_number"]},
            "rules_added": rules_added,
            "rules_removed": rules_removed,
            "rules_modified": rules_modified,
            "conditions_added": conditions_added,
            "conditions_removed": conditions_removed,
            "dependencies_added": dependencies_added,
            "dependencies_removed": dependencies_removed,
        }

    async def rollback(
        self,
        db: AsyncSession,
        playbook_id: UUID,
        target_version_id: UUID,
        user_id: UUID,
    ) -> None:
        """
        Restore a playbook to a previously saved snapshot.

        Steps:
        1. Load and validate target snapshot.
        2. Delete current dependencies, condition overrides, conditions,
           rule tiers, rule overrides, rules (in dependency order).
        3. Recreate all objects from the snapshot, preserving original UUIDs
           so that any external references (e.g. analytics) remain stable.
        4. Increment playbook.version.
        5. Create a new PlaybookVersion entry recording the rollback.
        """
        logger.info(
            "Rolling back playbook %s to version %s by user %s",
            playbook_id,
            target_version_id,
            user_id,
        )

        target = await self.get_version(db, target_version_id)
        if str(target["playbook_id"]) != str(playbook_id):
            raise ValueError(
                f"Version {target_version_id} does not belong to playbook {playbook_id}"
            )

        snap: Dict[str, Any] = target["snapshot"]

        # ------------------------------------------------------------------
        # 1. Wipe current data (cascade removes child rows, but we delete
        #    explicitly in safe order to avoid FK constraint violations on
        #    databases where CASCADE is not set at the DB level).
        # ------------------------------------------------------------------

        # Dependencies reference rules → delete first
        await db.execute(
            delete(PlaybookRuleDependency).where(
                PlaybookRuleDependency.playbook_id == playbook_id
            )
        )

        # Overrides reference conditions AND rules → delete before both
        # We reach them via condition rows for this playbook
        cond_ids_stmt = select(PlaybookCondition.id).where(
            PlaybookCondition.playbook_id == playbook_id
        )
        cond_ids_result = await db.execute(cond_ids_stmt)
        existing_cond_ids = [row[0] for row in cond_ids_result]

        if existing_cond_ids:
            await db.execute(
                delete(PlaybookRuleOverride).where(
                    PlaybookRuleOverride.condition_id.in_(existing_cond_ids)
                )
            )

        await db.execute(
            delete(PlaybookCondition).where(
                PlaybookCondition.playbook_id == playbook_id
            )
        )

        # Rule-level overrides that may still reference rules directly
        rule_ids_stmt = select(PlaybookRule.id).where(
            PlaybookRule.playbook_id == playbook_id
        )
        rule_ids_result = await db.execute(rule_ids_stmt)
        existing_rule_ids = [row[0] for row in rule_ids_result]

        if existing_rule_ids:
            await db.execute(
                delete(PlaybookRuleOverride).where(
                    PlaybookRuleOverride.rule_id.in_(existing_rule_ids)
                )
            )
            await db.execute(
                delete(PlaybookRuleTier).where(
                    PlaybookRuleTier.rule_id.in_(existing_rule_ids)
                )
            )

        await db.execute(
            delete(PlaybookRule).where(PlaybookRule.playbook_id == playbook_id)
        )

        # ------------------------------------------------------------------
        # 2. Recreate from snapshot
        # ------------------------------------------------------------------

        # Rules (and their tiers; overrides are recreated with conditions)
        rule_id_map: Dict[str, UUID] = {}  # old str(id) → new UUID
        for rule_data in snap.get("rules", []):
            new_rule_id = UUID(rule_data["id"])
            rule_id_map[rule_data["id"]] = new_rule_id

            rule = PlaybookRule(
                id=new_rule_id,
                playbook_id=playbook_id,
                clause_type=rule_data["clause_type"],
                primary_position=rule_data["primary_position"],
                fallback_position=rule_data.get("fallback_position"),
                risk_level=rule_data["risk_level"],
                is_deal_breaker=rule_data.get("is_deal_breaker", False),
                detection_patterns=rule_data.get("detection_patterns"),
                suggested_language=rule_data.get("suggested_language"),
                order_index=rule_data.get("order_index", 0),
                requires_ai_verification=rule_data.get("requires_ai_verification", True),
                verification_prompt=rule_data.get("verification_prompt"),
                jurisdiction_overrides=rule_data.get("jurisdiction_overrides"),
                priority=rule_data.get("priority", 50),
                category=rule_data.get("category"),
                subcategory=rule_data.get("subcategory"),
                tags=rule_data.get("tags"),
            )
            db.add(rule)

            for tier_data in rule_data.get("tiers", []):
                tier = PlaybookRuleTier(
                    id=UUID(tier_data["id"]),
                    rule_id=new_rule_id,
                    tier_level=tier_data["tier_level"],
                    position_text=tier_data["position_text"],
                    guidance_notes=tier_data.get("guidance_notes"),
                    risk_level_at_tier=tier_data.get("risk_level_at_tier", "yellow"),
                )
                db.add(tier)

        # Conditions (and their overrides)
        for cond_data in snap.get("conditions", []):
            new_cond_id = UUID(cond_data["id"])
            cond = PlaybookCondition(
                id=new_cond_id,
                playbook_id=playbook_id,
                name=cond_data["name"],
                description=cond_data.get("description"),
                condition_type=cond_data["condition_type"],
                operator=cond_data.get("operator", "equals"),
                condition_value=cond_data["condition_value"],
                is_active=cond_data.get("is_active", True),
                priority=cond_data.get("priority", 0),
            )
            db.add(cond)

            for ovr_data in cond_data.get("rule_overrides", []):
                # Resolve rule_id: use mapping if available, else original UUID
                raw_rule_id: str = ovr_data["rule_id"]
                resolved_rule_id: UUID = rule_id_map.get(raw_rule_id, UUID(raw_rule_id))
                override = PlaybookRuleOverride(
                    id=UUID(ovr_data["id"]),
                    condition_id=new_cond_id,
                    rule_id=resolved_rule_id,
                    override_risk_level=ovr_data.get("override_risk_level"),
                    override_position_text=ovr_data.get("override_position_text"),
                    override_is_deal_breaker=ovr_data.get("override_is_deal_breaker"),
                    override_tier_level=ovr_data.get("override_tier_level"),
                    suppress_rule=ovr_data.get("suppress_rule", False),
                    notes=ovr_data.get("notes"),
                )
                db.add(override)

        # Dependencies
        for dep_data in snap.get("dependencies", []):
            raw_src: str = dep_data["source_rule_id"]
            raw_tgt: str = dep_data["target_rule_id"]
            dep = PlaybookRuleDependency(
                id=UUID(dep_data["id"]),
                playbook_id=playbook_id,
                source_rule_id=rule_id_map.get(raw_src, UUID(raw_src)),
                target_rule_id=rule_id_map.get(raw_tgt, UUID(raw_tgt)),
                trigger_condition=dep_data["trigger_condition"],
                effect=dep_data["effect"],
                effect_params=dep_data.get("effect_params"),
                is_active=dep_data.get("is_active", True),
            )
            db.add(dep)

        # ------------------------------------------------------------------
        # 3. Update playbook.version and metadata
        # ------------------------------------------------------------------
        stmt = select(Playbook).where(Playbook.id == playbook_id)
        res = await db.execute(stmt)
        playbook = res.scalar_one()
        playbook.version = playbook.version + 1
        playbook.updated_at = datetime.now(timezone.utc)

        # ------------------------------------------------------------------
        # 4. Create rollback version entry
        # ------------------------------------------------------------------
        rollback_version_number = await self._next_version_number(db, playbook_id)
        rollback_summary = (
            f"Rollback to version {target['version_number']} "
            f"(snapshot id: {target_version_id})"
        )
        rollback_version = PlaybookVersion(
            id=uuid.uuid4(),
            playbook_id=playbook_id,
            version_number=rollback_version_number,
            snapshot=snap,
            change_summary=rollback_summary,
            created_by=user_id,
            created_at=datetime.now(timezone.utc),
        )
        db.add(rollback_version)

        await db.commit()

        logger.info(
            "Rollback complete: playbook %s restored to snapshot v%d; "
            "new version entry v%d created",
            playbook_id,
            target["version_number"],
            rollback_version_number,
        )


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

playbook_versioning_service = PlaybookVersioningService()
