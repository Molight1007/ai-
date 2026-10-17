"""backend.builder —— 静态扫描 → 骨架 IR。

用 __getattr__ 延迟加载，避免 `python -m backend.builder.builder` 的模块重复加载警告。
"""

__all__ = ["build_ir"]


def __getattr__(name):
    if name == "build_ir":
        from . import builder

        return builder.build_ir
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
