"""IR schema v2 —— 常量与约束定义（唯一契约）。

这份文件定义「合法 IR 长什么样」，供校验器（validate.py）、
Builder 产出方（含 WorkBuddy 语义填充）与前端渲染共同对齐。

只允许标准库，零第三方依赖。
"""

from __future__ import annotations

# ---- 版本 ----
SCHEMA_VERSION = 2

# ---- 命名与枚举 ----
# 节点 id：字母开头，仅字母/数字/-/_
ID_RE = r"^[a-zA-Z][a-zA-Z0-9_-]*$"

SEVERITIES = ("error", "warning", "info")
LAYERS = ("L0", "L1", "L2", "L3", "L4", "L5")
DEP_TYPES = ("import", "call", "inherit", "reference")

# ---- 必填字段表（用于 IR/MISSING_KEY 检测）----
REQUIRED_TOP = ("schema_version", "meta", "modules", "files")

REQUIRED_META = ("project", "language", "generated_by")

REQUIRED_MODULE = ("id", "label")
REQUIRED_FILE = ("id", "path", "module")
REQUIRED_FUNCTION = ("id", "name")
REQUIRED_DEP = ("from", "to")
REQUIRED_MODDEP = ("from", "to")
REQUIRED_FLOW = ("id", "label", "steps")
REQUIRED_VIOLATION = ("id", "rule", "node")
REQUIRED_FINDING = ("id", "severity", "node", "title")

# ---- 可选字段白名单（未列出的未知字段不报错，仅作参考）----
# 注意：本校验器不做「未知字段」校验，避免误伤前向兼容。
