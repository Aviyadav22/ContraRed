"""
Playbook Conditions Engine - Phase 6 Conditional Logic.

Evaluates PlaybookCondition records against a DealContext (counterparty type,
deal size, jurisdiction, contract side) and applies PlaybookRuleOverride records
to a list of RuleMatch objects produced by the RuleEngine.

This allows playbook rules to adapt dynamically depending on who the deal is
with, how large the deal is, which legal system governs it, and which side of
the contract the client is on.

Usage:
    deal_context = DealContext(
        counterparty_type="fortune_500",
        deal_size=1_500_000.0,
        jurisdiction="CA-US",
        contract_side="vendor",
    )
    modified_matches = await conditions_engine.process(
        db=db,
        playbook_id=playbook_id,
        deal_context=deal_context,
        matches=rule_matches,
    )
"""

import copy
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.playbook import PlaybookCondition, PlaybookRuleOverride
from app.services.rule_engine import RiskLevel, RuleMatch

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# DealContext
# ---------------------------------------------------------------------------

@dataclass
class DealContext:
    """Contextual metadata for a specific contract deal.

    All fields are optional so callers can supply only what is known at the
    time of analysis.  The engine skips condition checks whose required field
    is absent from the context (i.e. the condition does NOT match).

    Attributes:
        counterparty_type: Classification of the other party.
            Common values: "fortune_500", "startup", "government", "mid_market",
            "smb", "individual".
        deal_size: Total contract value in USD.
        jurisdiction: Jurisdiction code using ISO 3166 or custom codes.
            Examples: "IN" (India), "CA-US" (California, USA), "UK", "DE".
        contract_side: Which side of the contract the client occupies.
            Either "vendor" (providing goods/services) or "customer" (receiving
            them).  Some contracts call these "licensor"/"licensee" or
            "service_provider"/"client" — normalize to vendor/customer before
            passing in.
        custom_fields: Arbitrary key-value pairs for extensibility.
            Example: {"industry": "fintech", "is_regulated": True}
    """

    counterparty_type: Optional[str] = None
    deal_size: Optional[float] = None
    jurisdiction: Optional[str] = None
    contract_side: Optional[str] = None
    custom_fields: Optional[Dict[str, Any]] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# ConditionsEngine
# ---------------------------------------------------------------------------

class ConditionsEngine:
    """Evaluates conditional playbook logic against a deal context.

    The engine performs three operations:

    1. ``evaluate_conditions`` – Given a list of PlaybookCondition rows and a
       DealContext, return only the conditions that *match* the context.

    2. ``apply_overrides`` – Given a list of RuleMatch objects and the
       PlaybookRuleOverride rows collected from matching conditions, mutate
       (or suppress) the matches according to each override.

    3. ``process`` (async) – Full pipeline: load from DB, evaluate, apply,
       return.
    """

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def evaluate_conditions(
        self,
        conditions: List[PlaybookCondition],
        deal_context: DealContext,
    ) -> List[PlaybookCondition]:
        """Return conditions that match *deal_context*, sorted by priority desc.

        A condition is considered matching when:
          - it is marked ``is_active=True``, AND
          - the operator logic defined by its ``condition_type``, ``operator``,
            and ``condition_value`` is satisfied by the corresponding field in
            *deal_context*.

        If the required context field is ``None`` (caller did not supply it),
        the condition is skipped (does NOT match).

        Args:
            conditions: All PlaybookCondition records for the playbook.
            deal_context: The contextual metadata for the current deal.

        Returns:
            Subset of *conditions* that match, sorted descending by priority.
        """
        matched: List[PlaybookCondition] = []

        for condition in conditions:
            if not condition.is_active:
                logger.debug(
                    "Skipping inactive condition id=%s name=%r",
                    condition.id,
                    condition.name,
                )
                continue

            try:
                if self._evaluate_single(condition, deal_context):
                    matched.append(condition)
                    logger.debug(
                        "Condition matched: id=%s name=%r priority=%d",
                        condition.id,
                        condition.name,
                        condition.priority,
                    )
            except Exception as exc:  # pragma: no cover – defensive
                logger.warning(
                    "Error evaluating condition id=%s name=%r: %s",
                    condition.id,
                    condition.name,
                    exc,
                    exc_info=True,
                )

        # Higher priority number = evaluated first / takes precedence
        matched.sort(key=lambda c: c.priority, reverse=True)
        logger.info(
            "evaluate_conditions: %d/%d conditions matched for deal_context=%r",
            len(matched),
            len(conditions),
            deal_context,
        )
        return matched

    def apply_overrides(
        self,
        matches: List[RuleMatch],
        overrides: List[PlaybookRuleOverride],
        rule_id_to_clause_type: Optional[Dict[str, str]] = None,
    ) -> List[RuleMatch]:
        """Apply a list of PlaybookRuleOverride records to a list of RuleMatch objects.

        Overrides are keyed on the UUID of the PlaybookRule.  Each RuleMatch
        carries ``rule_id`` which is set to the PlaybookRule UUID (via
        ``RuleEngine.from_playbook_rules``).  For default built-in rules the
        ``rule_id`` is a short string like ``"unlimited_liability"``; in that
        case the caller can pass *rule_id_to_clause_type* as a fallback lookup
        by ``clause_type``.

        Override application order:
          1. ``suppress_rule=True``   → remove the match entirely
          2. ``override_risk_level``  → change risk level (string → RiskLevel)
          3. ``override_position_text`` → replace primary_position
          4. ``override_is_deal_breaker`` → change is_deal_breaker flag

        Overrides from higher-priority conditions are applied first (caller is
        responsible for ordering *overrides* before calling this method, or
        ensure they come from a sorted condition list).

        Args:
            matches: List of RuleMatch objects from the RuleEngine.
            overrides: Flattened list of PlaybookRuleOverride objects collected
                from all matching conditions.
            rule_id_to_clause_type: Optional mapping of PlaybookRule UUID string
                → clause_type string, used as fallback when a match's rule_id is
                not a UUID.

        Returns:
            A new list of RuleMatch objects with overrides applied.  The
            original list is not mutated.
        """
        if not overrides:
            return list(matches)

        rule_id_to_clause_type = rule_id_to_clause_type or {}

        # Build a mutable copy – we work on copies of each match so the
        # originals are never mutated in place.
        working: List[RuleMatch] = [copy.copy(m) for m in matches]

        # Track which match indices to suppress (delete after iteration)
        suppress_indices: set = set()
        # Track which match indices have already been modified by a higher-priority override
        modified_indices: set = set()

        for override in overrides:
            rule_uuid_str = str(override.rule_id)

            # Determine the target clause_type for fallback matching
            target_clause_type = rule_id_to_clause_type.get(rule_uuid_str)

            for idx, match in enumerate(working):
                if idx in suppress_indices:
                    continue  # Already suppressed by an earlier override

                if idx in modified_indices:
                    continue  # Higher-priority override already applied — skip

                if not self._override_targets_match(
                    match, rule_uuid_str, target_clause_type
                ):
                    continue

                # --- 1. Suppress ---
                if override.suppress_rule:
                    suppress_indices.add(idx)
                    logger.info(
                        "Suppressing match clause_type=%r due to override id=%s",
                        match.clause_type,
                        override.id,
                    )
                    continue  # No further processing for this match

                # Mark as modified so lower-priority overrides don't overwrite
                modified_indices.add(idx)

                # --- 2. Risk level ---
                if override.override_risk_level is not None:
                    new_risk = self._parse_risk_level(override.override_risk_level)
                    if new_risk is not None:
                        logger.info(
                            "Override risk %s -> %s for clause_type=%r (override id=%s)",
                            match.risk_level.value,
                            new_risk.value,
                            match.clause_type,
                            override.id,
                        )
                        match.risk_level = new_risk

                # --- 3. Position text ---
                if override.override_position_text is not None:
                    logger.debug(
                        "Override position_text for clause_type=%r (override id=%s)",
                        match.clause_type,
                        override.id,
                    )
                    match.primary_position = override.override_position_text

                # --- 4. Deal-breaker flag ---
                if override.override_is_deal_breaker is not None:
                    match.is_deal_breaker = override.override_is_deal_breaker

        # Build result, excluding suppressed entries
        result = [m for i, m in enumerate(working) if i not in suppress_indices]
        logger.info(
            "apply_overrides: %d overrides processed; %d matches suppressed; %d matches returned",
            len(overrides),
            len(suppress_indices),
            len(result),
        )
        return result

    async def process(
        self,
        db: AsyncSession,
        playbook_id: UUID,
        deal_context: DealContext,
        matches: List[RuleMatch],
    ) -> List[RuleMatch]:
        """Full pipeline: load conditions from DB, evaluate, apply overrides.

        Steps:
          1. Load all active PlaybookCondition rows for *playbook_id*, eagerly
             loading their ``rule_overrides`` and each override's ``rule``
             relationship (for clause_type lookup).
          2. Evaluate which conditions match *deal_context*.
          3. Collect all PlaybookRuleOverride objects from the matched conditions
             (preserving priority order).
          4. Build a rule_id_to_clause_type mapping for fallback matching.
          5. Apply overrides to *matches* and return the modified list.

        Args:
            db: An open AsyncSession.
            playbook_id: UUID of the playbook whose conditions to load.
            deal_context: Deal metadata to evaluate conditions against.
            matches: RuleMatch list produced by the RuleEngine before calling
                this method.

        Returns:
            Modified (or filtered) list of RuleMatch objects.  Order is
            preserved; suppressed matches are removed.
        """
        logger.info(
            "process: loading conditions for playbook_id=%s", playbook_id
        )

        # ----- Load conditions with their overrides and rule relationships -----
        stmt = (
            select(PlaybookCondition)
            .where(
                PlaybookCondition.playbook_id == playbook_id,
                PlaybookCondition.is_active.is_(True),
            )
            .options(
                selectinload(PlaybookCondition.rule_overrides).selectinload(
                    PlaybookRuleOverride.rule
                )
            )
            .order_by(PlaybookCondition.priority.desc())
        )

        result = await db.execute(stmt)
        conditions: List[PlaybookCondition] = list(result.scalars().all())

        if not conditions:
            logger.info(
                "process: no active conditions found for playbook_id=%s; "
                "returning matches unchanged",
                playbook_id,
            )
            return list(matches)

        # ----- Evaluate which conditions match the deal context -----
        matched_conditions = self.evaluate_conditions(conditions, deal_context)

        if not matched_conditions:
            logger.info(
                "process: no conditions matched deal_context=%r; "
                "returning matches unchanged",
                deal_context,
            )
            return list(matches)

        # ----- Collect overrides from matching conditions (priority order) -----
        all_overrides: List[PlaybookRuleOverride] = []
        rule_id_to_clause_type: Dict[str, str] = {}

        for condition in matched_conditions:
            for override in condition.rule_overrides:
                all_overrides.append(override)
                # Build fallback mapping using the eager-loaded rule
                if override.rule is not None:
                    rule_id_to_clause_type[str(override.rule_id)] = (
                        override.rule.clause_type
                    )

        logger.info(
            "process: %d overrides collected from %d matching conditions",
            len(all_overrides),
            len(matched_conditions),
        )

        # ----- Apply overrides -----
        return self.apply_overrides(matches, all_overrides, rule_id_to_clause_type)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _evaluate_single(
        self,
        condition: PlaybookCondition,
        deal_context: DealContext,
    ) -> bool:
        """Return True if *condition* is satisfied by *deal_context*.

        Dispatches to the appropriate evaluator based on condition_type.
        """
        ctype = (condition.condition_type or "").lower()
        operator = (condition.operator or "").lower()
        cv: Dict[str, Any] = condition.condition_value or {}

        if ctype == "counterparty_type":
            return self._eval_string_field(
                deal_context.counterparty_type, operator, cv, ctype
            )

        if ctype == "deal_size":
            return self._eval_numeric_field(
                deal_context.deal_size, operator, cv, ctype
            )

        if ctype == "jurisdiction":
            return self._eval_string_field(
                deal_context.jurisdiction, operator, cv, ctype
            )

        if ctype == "contract_side":
            return self._eval_string_field(
                deal_context.contract_side, operator, cv, ctype
            )

        if ctype == "custom":
            return self._eval_custom_field(
                deal_context.custom_fields, operator, cv
            )

        logger.warning(
            "Unknown condition_type=%r for condition id=%s; treating as no-match",
            ctype,
            condition.id,
        )
        return False

    def _eval_string_field(
        self,
        context_value: Optional[str],
        operator: str,
        cv: Dict[str, Any],
        field_name: str,
    ) -> bool:
        """Evaluate string-based condition operators.

        Supported operators: equals, not_equals, in, not_in.
        """
        if context_value is None:
            logger.debug(
                "Context field %r is None; condition cannot match", field_name
            )
            return False

        # Normalize to lower-case for case-insensitive comparison
        ctx = context_value.lower()

        if operator == "equals":
            expected = str(cv.get("value", "")).lower()
            return ctx == expected

        if operator == "not_equals":
            expected = str(cv.get("value", "")).lower()
            return ctx != expected

        if operator == "in":
            values = [str(v).lower() for v in cv.get("values", [])]
            return ctx in values

        if operator == "not_in":
            values = [str(v).lower() for v in cv.get("values", [])]
            return ctx not in values

        # "contains" makes semantic sense for string fields too
        if operator == "contains":
            expected = str(cv.get("value", "")).lower()
            return expected in ctx

        logger.warning(
            "Unsupported operator %r for string field %r; treating as no-match",
            operator,
            field_name,
        )
        return False

    def _eval_numeric_field(
        self,
        context_value: Optional[float],
        operator: str,
        cv: Dict[str, Any],
        field_name: str,
    ) -> bool:
        """Evaluate numeric condition operators for deal_size.

        Supported operators: equals, not_equals, greater_than, less_than,
        between (stored as operator="between" with min/max in condition_value).
        """
        if context_value is None:
            logger.debug(
                "Context field %r is None; condition cannot match", field_name
            )
            return False

        if operator == "greater_than":
            threshold = self._to_float(cv.get("threshold"))
            if threshold is None:
                return False
            return context_value > threshold

        if operator == "less_than":
            threshold = self._to_float(cv.get("threshold"))
            if threshold is None:
                return False
            return context_value < threshold

        if operator == "equals":
            threshold = self._to_float(cv.get("threshold") or cv.get("value"))
            if threshold is None:
                return False
            return context_value == threshold

        if operator == "not_equals":
            threshold = self._to_float(cv.get("threshold") or cv.get("value"))
            if threshold is None:
                return False
            return context_value != threshold

        if operator == "between":
            # condition_value: {"min": <number>, "max": <number>}
            min_val = self._to_float(cv.get("min"))
            max_val = self._to_float(cv.get("max"))
            if min_val is None or max_val is None:
                logger.warning(
                    "Condition operator 'between' missing 'min'/'max' in "
                    "condition_value=%r; treating as no-match",
                    cv,
                )
                return False
            return min_val <= context_value <= max_val

        logger.warning(
            "Unsupported operator %r for numeric field %r; treating as no-match",
            operator,
            field_name,
        )
        return False

    def _eval_custom_field(
        self,
        custom_fields: Optional[Dict[str, Any]],
        operator: str,
        cv: Dict[str, Any],
    ) -> bool:
        """Evaluate custom-field conditions.

        condition_value is expected to carry:
          - "key": the key inside DealContext.custom_fields to inspect
          - "value": the value to compare against

        Supported operators: equals, not_equals, contains, in, not_in.
        """
        if not custom_fields:
            logger.debug("custom_fields is empty/None; custom condition cannot match")
            return False

        key = cv.get("key")
        if key is None:
            logger.warning(
                "Custom condition missing 'key' in condition_value=%r; treating as no-match",
                cv,
            )
            return False

        field_value = custom_fields.get(key)
        if field_value is None:
            return False

        if operator == "equals":
            return str(field_value).lower() == str(cv.get("value", "")).lower()

        if operator == "not_equals":
            return str(field_value).lower() != str(cv.get("value", "")).lower()

        if operator == "contains":
            # Works for string fields or list fields
            expected = cv.get("value")
            if isinstance(field_value, list):
                return expected in field_value
            return str(expected).lower() in str(field_value).lower()

        if operator == "in":
            allowed = cv.get("values", [])
            return field_value in allowed or str(field_value).lower() in [
                str(v).lower() for v in allowed
            ]

        if operator == "not_in":
            allowed = cv.get("values", [])
            return field_value not in allowed and str(field_value).lower() not in [
                str(v).lower() for v in allowed
            ]

        logger.warning(
            "Unsupported operator %r for custom field; treating as no-match",
            operator,
        )
        return False

    @staticmethod
    def _override_targets_match(
        match: RuleMatch,
        rule_uuid_str: str,
        target_clause_type: Optional[str],
    ) -> bool:
        """Return True if *override* targets *match*.

        Primary key: match.rule_id == rule_uuid_str (UUID-to-UUID).
        Fallback:    match.clause_type == target_clause_type (for built-in rules
                     whose rule_id is a short slug, not a UUID).
        """
        if match.rule_id == rule_uuid_str:
            return True
        if target_clause_type and match.clause_type == target_clause_type:
            return True
        return False

    @staticmethod
    def _parse_risk_level(value: str) -> Optional[RiskLevel]:
        """Convert an override string value to a RiskLevel enum member.

        Accepts "RED", "YELLOW", "GREEN" (case-insensitive).
        Returns None if the value is not recognised.
        """
        normalized = value.upper().strip()
        try:
            return RiskLevel(normalized)
        except ValueError:
            logger.warning(
                "Unrecognised risk level value %r in override; skipping risk change",
                value,
            )
            return None

    @staticmethod
    def _to_float(value: Any) -> Optional[float]:
        """Safely convert a value from JSONB to float.

        Returns None if conversion fails, logging a warning.
        """
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            logger.warning(
                "Cannot convert condition_value entry %r to float", value
            )
            return None


# ---------------------------------------------------------------------------
# Module singleton
# ---------------------------------------------------------------------------

conditions_engine = ConditionsEngine()
"""Module-level singleton.  Import and use directly:

    from app.services.playbook_conditions_engine import conditions_engine, DealContext

    modified = await conditions_engine.process(db, playbook_id, deal_context, matches)
"""
