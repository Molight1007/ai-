"""backend.rules —— AI 代码规范规则集 + 静态规则引擎。

用 __getattr__ 延迟加载 engine，避免 `python -m backend.rules.engine` 时
因包内 eager import 造成的模块重复加载警告。
"""

__all__ = ["Violation", "analyze", "load_rules"]


def __getattr__(name):
    if name in ("Violation", "analyze", "load_rules"):
        from . import engine

        return getattr(engine, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
