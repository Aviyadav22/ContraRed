"""
Cross-Clause Dependency Resolver — Phase 6

Runs AFTER the rule engine has evaluated all clauses.  It walks the
PlaybookRuleDependency graph, checks each dependency's trigger_condition
against the source rule's current state, and applies the specified effect
to the target rule.

Supported trigger conditions
------------------------------
  source_is_red        — source risk_level == RED
  source_is_yellow     — source risk_level == YELLOW
  source_missing       — source clause_type not found in any match
  source_uncapped      — "uncapped" or "unlimited" appears in source match_text
  source_deal_breaker  — source is_deal_breaker is True

Supported effects
-----------------
  escalate_risk    — set target risk_level to effect_params["new_risk"]
  add_flag         — append effect_params["message"] to target's flags list
  change_position  — override target primary_position with effect_params["new_position"]
  suppress         — remove target from the results list entirely

Cycle detection
---------------
  If a dependency cycle is detected (A→B→A), the offending edge is logged
  as a warning and skipped.
"""

from __future__ import annotations

import logging
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from app.services.rule_engine import RiskLevel, RuleMatch

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Public data structures
# ---------------------------------------------------------------------------

# Mirrors the essential columns from the PlaybookRuleDependency ORM model.
# We use a plain dataclass so this module has no SQLAlchemy import dependency.
@dataclass
class PlaybookRuleDependency:
    """Lightweight mirror of the ORM model for resolver use.

    Fields match PlaybookRuleDependency ORM columns.
    """
    source_rule_id: str          # clause_type of the source rule
    target_rule_id: str          # clause_type of the target rule
    trigger_condition: str       # e.g. "source_is_red"
    effect: str                  # e.g. "escalate_risk"
    effect_params: Dict[str, Any] = field(default_factory=dict)  # JSONB payload
    is_active: bool = True
    playbook_id: Optional[str] = None


@dataclass
class DependencyAction:
    """Record of a single dependency application for audit / telemetry."""
    source_clause: str
    target_clause: str
    trigger: str
    effect: str
    message: str


# ---------------------------------------------------------------------------
# Resolver
# ---------------------------------------------------------------------------

class DependencyResolver:
    """Cascades risk adjustments across clauses based on dependency rules.

    Usage::

        resolver = DependencyResolver()
        modified_matches, actions = resolver.resolve(rule_matches, dependencies)
    """

    # ------------------------------------------------------------------ #
    # Trigger evaluation
    # ------------------------------------------------------------------ #

    def _evaluate_trigger(
        self,
        condition: str,
        source_match: Optional[RuleMatch],
    ) -> bool:
        """Return True if *condition* is satisfied given *source_match*.

        Parameters
        ----------
        condition:
            One of the documented trigger condition strings.
        source_match:
            The RuleMatch for the source clause, or None if not found.
        """
        if condition == "source_missing":
            return source_match is None

        if source_match is None:
            # Remaining conditions all require the source to be present.
            return False

        if condition == "source_is_red":
            return source_match.risk_level == RiskLevel.RED

        if condition == "source_is_yellow":
            return source_match.risk_level == RiskLevel.YELLOW

        if condition == "source_uncapped":
            text_lower = source_match.match_text.lower()
            return "uncapped" in text_lower or "unlimited" in text_lower

        if condition == "source_deal_breaker":
            return source_match.is_deal_breaker

        logger.warning(
            "DependencyResolver: unknown trigger_condition %r — skipping",
            condition,
        )
        return False

    # ------------------------------------------------------------------ #
    # Effect application
    # ------------------------------------------------------------------ #

    def _apply_effect(
        self,
        effect: str,
        effect_params: Dict[str, Any],
        target_match: Optional[RuleMatch],
        results: List[RuleMatch],
        dep: PlaybookRuleDependency,
        actions: List[DependencyAction],
    ) -> None:
        """Mutate *results* and append to *actions* according to *effect*.

        Parameters
        ----------
        effect:
            One of the documented effect strings.
        effect_params:
            JSONB payload associated with the dependency row.
        target_match:
            The RuleMatch for the target clause, or None if not found.
        results:
            The mutable working copy of RuleMatch objects.
        dep:
            The dependency row (used for logging).
        actions:
            Accumulated list of DependencyAction records.
        """
        if effect == "escalate_risk":
            if target_match is None:
                logger.debug(
                    "escalate_risk: target clause %r not in results — no-op",
                    dep.target_rule_id,
                )
                return
            raw = effect_params.get("new_risk", "").upper()
            try:
                new_level = RiskLevel(raw)
            except ValueError:
                logger.warning(
                    "escalate_risk: invalid new_risk value %r for target %r",
                    raw,
                    dep.target_rule_id,
                )
                return
            old_level = target_match.risk_level
            target_match.risk_level = new_level
            msg = (
                f"Risk escalated {old_level.value} → {new_level.value} "
                f"due to dependency from {dep.source_rule_id}"
            )
            actions.append(
                DependencyAction(
                    source_clause=dep.source_rule_id,
                    target_clause=dep.target_rule_id,
                    trigger=dep.trigger_condition,
                    effect=effect,
                    message=msg,
                )
            )
            logger.debug(msg)

        elif effect == "add_flag":
            if target_match is None:
                logger.debug(
                    "add_flag: target clause %r not in results — no-op",
                    dep.target_rule_id,
                )
                return
            message = effect_params.get("message", "")
            # Store flags in escalation_reason (append, |-separated) since
            # RuleMatch has no dedicated flags list.  Callers can split on "|".
            if target_match.escalation_reason:
                target_match.escalation_reason = (
                    f"{target_match.escalation_reason} | {message}"
                )
            else:
                target_match.escalation_reason = message
            msg = (
                f"Flag added to {dep.target_rule_id}: {message!r} "
                f"(triggered by {dep.source_rule_id})"
            )
            actions.append(
                DependencyAction(
                    source_clause=dep.source_rule_id,
                    target_clause=dep.target_rule_id,
                    trigger=dep.trigger_condition,
                    effect=effect,
                    message=msg,
                )
            )
            logger.debug(msg)

        elif effect == "change_position":
            if target_match is None:
                logger.debug(
                    "change_position: target clause %r not in results — no-op",
                    dep.target_rule_id,
                )
                return
            new_pos = effect_params.get("new_position", "")
            old_pos = target_match.primary_position
            target_match.primary_position = new_pos
            msg = (
                f"Position overridden on {dep.target_rule_id}: "
                f"{old_pos!r} → {new_pos!r} "
                f"(triggered by {dep.source_rule_id})"
            )
            actions.append(
                DependencyAction(
                    source_clause=dep.source_rule_id,
                    target_clause=dep.target_rule_id,
                    trigger=dep.trigger_condition,
                    effect=effect,
                    message=msg,
                )
            )
            logger.debug(msg)

        elif effect == "suppress":
            if target_match is None:
                logger.debug(
                    "suppress: target clause %r not in results — no-op",
                    dep.target_rule_id,
                )
                return
            results.remove(target_match)
            msg = (
                f"Clause {dep.target_rule_id} suppressed "
                f"due to dependency from {dep.source_rule_id}"
            )
            actions.append(
                DependencyAction(
                    source_clause=dep.source_rule_id,
                    target_clause=dep.target_rule_id,
                    trigger=dep.trigger_condition,
                    effect=effect,
                    message=msg,
                )
            )
            logger.debug(msg)

        else:
            logger.warning(
                "DependencyResolver: unknown effect %r — skipping",
                effect,
            )

    # ------------------------------------------------------------------ #
    # Cycle detection
    # ------------------------------------------------------------------ #

    @staticmethod
    def _build_adjacency(
        deps: List[PlaybookRuleDependency],
    ) -> Dict[str, Set[str]]:
        """Return adjacency map {source_clause_type → {target_clause_type, …}}."""
        graph: Dict[str, Set[str]] = {}
        for dep in deps:
            if not dep.is_active:
                continue
            graph.setdefault(dep.source_rule_id, set()).add(dep.target_rule_id)
        return graph

    @classmethod
    def _detect_cycles(
        cls,
        graph: Dict[str, Set[str]],
    ) -> Set[Tuple[str, str]]:
        """Return set of (source, target) edges that form part of a cycle.

        Uses iterative DFS with colouring to avoid RecursionError on deep graphs:
          WHITE (0) = unvisited
          GRAY  (1) = in current path
          BLACK (2) = fully processed
        """
        WHITE, GRAY, BLACK = 0, 1, 2
        color: Dict[str, int] = {}
        cyclic_edges: Set[Tuple[str, str]] = set()

        for start_node in list(graph.keys()):
            if color.get(start_node, WHITE) != WHITE:
                continue

            # Explicit stack: (node, iterator_over_neighbours)
            stack: list = [(start_node, iter(graph.get(start_node, set())))]
            color[start_node] = GRAY

            while stack:
                node, neighbours_iter = stack[-1]
                advanced = False
                for neighbour in neighbours_iter:
                    if color.get(neighbour, WHITE) == GRAY:
                        # Back-edge → cycle
                        cyclic_edges.add((node, neighbour))
                        logger.warning(
                            "DependencyResolver: cycle detected %r → %r — "
                            "this edge will be skipped",
                            node,
                            neighbour,
                        )
                    elif color.get(neighbour, WHITE) == WHITE:
                        color[neighbour] = GRAY
                        stack.append((neighbour, iter(graph.get(neighbour, set()))))
                        advanced = True
                        break
                    # BLACK neighbours are already fully processed — skip
                if not advanced:
                    color[node] = BLACK
                    stack.pop()

        return cyclic_edges

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def resolve(
        self,
        matches: List[RuleMatch],
        dependencies: List[PlaybookRuleDependency],
    ) -> Tuple[List[RuleMatch], List[DependencyAction]]:
        """Evaluate all dependencies and return updated matches + audit trail.

        Parameters
        ----------
        matches:
            Output of the rule engine for a single document.  The list is
            deep-copied internally; the caller's original list is untouched.
        dependencies:
            PlaybookRuleDependency rows for the active playbook.  Only rows
            with is_active=True are processed.

        Returns
        -------
        Tuple[List[RuleMatch], List[DependencyAction]]
            * Modified copy of *matches* with effects applied.
            * List of DependencyAction objects (one per triggered dependency).
        """
        if not dependencies:
            return matches, []

        # Work on a deep copy so callers retain the unmodified original.
        results: List[RuleMatch] = deepcopy(matches)
        actions: List[DependencyAction] = []

        # Filter to active dependencies only.
        active_deps = [d for d in dependencies if d.is_active]

        # Cycle detection across active deps.
        graph = self._build_adjacency(active_deps)
        cyclic_edges = self._detect_cycles(graph)

        # Build clause_type → RuleMatch lookup (first occurrence wins).
        clause_map: Dict[str, RuleMatch] = {}
        for m in results:
            if m.clause_type not in clause_map:
                clause_map[m.clause_type] = m

        for dep in active_deps:
            # Skip cyclic edges.
            if (dep.source_rule_id, dep.target_rule_id) in cyclic_edges:
                logger.warning(
                    "DependencyResolver: skipping cyclic edge %r → %r",
                    dep.source_rule_id,
                    dep.target_rule_id,
                )
                continue

            source_match = clause_map.get(dep.source_rule_id)
            triggered = self._evaluate_trigger(dep.trigger_condition, source_match)

            if not triggered:
                continue

            # Re-fetch target from results (it may have been suppressed already).
            target_match: Optional[RuleMatch] = next(
                (m for m in results if m.clause_type == dep.target_rule_id),
                None,
            )

            self._apply_effect(
                effect=dep.effect,
                effect_params=dep.effect_params,
                target_match=target_match,
                results=results,
                dep=dep,
                actions=actions,
            )

            # Refresh clause_map after potential suppression.
            clause_map = {}
            for m in results:
                if m.clause_type not in clause_map:
                    clause_map[m.clause_type] = m

        logger.info(
            "DependencyResolver: %d dependencies evaluated, %d actions applied",
            len(active_deps),
            len(actions),
        )
        return results, actions


# ---------------------------------------------------------------------------
# Singleton module instance
# ---------------------------------------------------------------------------

dependency_resolver = DependencyResolver()
