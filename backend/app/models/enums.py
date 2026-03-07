"""
Shared enums used across multiple models.
Defined once to avoid duplicate PostgreSQL enum types.
"""

import enum


class RiskLevel(str, enum.Enum):
    RED = "red"
    YELLOW = "yellow"
    GREEN = "green"
