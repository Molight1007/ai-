"""backend.ir —— IR 契约（schema v2）与校验器。"""

from .schema import SCHEMA_VERSION
from .validate import Issue, validate, errors_only

__all__ = ["SCHEMA_VERSION", "Issue", "validate", "errors_only"]
