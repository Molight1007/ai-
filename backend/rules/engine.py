"""规则引擎：按 code-rules.toml 对 Python 项目做静态自检，产出 rule_violations。

设计要点：
- 纯标准库（ast + tomllib），零第三方依赖，机器确定性判定（不靠 LLM）。
- 每条违规带 rule / path / name / line / end_line / detail / suggestion / severity，
  后续 Builder（P5）映射到 IR 的 rule_violations（node = 函数/文件 id）。

用法：
    python -m backend.rules.engine <项目目录>
"""

from __future__ import annotations

import ast
import os
import tomllib
from dataclasses import asdict, dataclass

DEFAULT_RULES = os.path.join(os.path.dirname(__file__), "code-rules.toml")

# 跳过这些目录（虚拟环境 / 缓存 / 第三方 / 隐藏目录）
_SKIP_DIRS = {
    "__pycache__", ".git", ".venv", "venv", "env", "node_modules",
    ".idea", ".vscode", "dist", "build", ".mypy_cache", ".pytest_cache",
}


@dataclass
class Violation:
    rule: str
    path: str
    name: str | None          # 函数/类名；文件级规则为 None
    line: int | None
    end_line: int | None
    detail: str
    suggestion: str = ""
    severity: str = "warning"


def load_rules(path: str = DEFAULT_RULES) -> dict:
    with open(path, "rb") as fp:
        return tomllib.load(fp)


def iter_py_files(root: str):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS and not d.startswith(".")]
        for fn in sorted(filenames):
            if fn.endswith(".py"):
                yield os.path.join(dirpath, fn)


def _rel(root: str, path: str) -> str:
    return os.path.relpath(path, root).replace("\\", "/")


def analyze(root: str, rules: dict) -> list[Violation]:
    rules = rules.get("rules", rules)
    out: list[Violation] = []
    for path in iter_py_files(root):
        rp = _rel(root, path)
        with open(path, "r", encoding="utf-8") as fp:
            src = fp.read()
        nlines = src.count("\n") + 1
        try:
            tree = ast.parse(src)
        except SyntaxError:
            continue
        out.extend(_check_file(rp, nlines, tree, rules))
    return out


def _cfg(rules: dict, name: str) -> dict:
    return rules.get(name, {}) if isinstance(rules, dict) else {}


def _check_file(rp: str, nlines: int, tree: ast.AST, rules: dict) -> list[Violation]:
    vs: list[Violation] = []

    cfg = _cfg(rules, "R_FILE_LEN")
    if cfg.get("enabled", True):
        limit = cfg.get("max_lines", 800)
        if nlines > limit:
            vs.append(Violation(
                "R_FILE_LEN", rp, None, 1, nlines,
                f"文件 {nlines} 行，超 {limit} 行硬线", "拆分为多个文件",
                cfg.get("severity", "warning"),
            ))

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            vs.extend(_check_func(rp, node, rules))
        elif isinstance(node, ast.ClassDef):
            vs.extend(_check_class(rp, node, rules))
        elif isinstance(node, ast.ExceptHandler):
            cfg = _cfg(rules, "R_BARE_EXCEPT")
            if cfg.get("enabled", True) and node.type is None:
                vs.append(Violation(
                    "R_BARE_EXCEPT", rp, None, node.lineno, None,
                    "裸 except 会吞掉所有异常", "明确捕获具体异常类型",
                    cfg.get("severity", "warning"),
                ))

    return vs


def _check_func(rp: str, node: ast.AST, rules: dict) -> list[Violation]:
    vs: list[Violation] = []
    end = getattr(node, "end_lineno", None) or node.lineno

    cfg = _cfg(rules, "R_FUNC_LEN")
    if cfg.get("enabled", True):
        limit = cfg.get("max_lines", 150)
        length = end - node.lineno + 1
        if length > limit:
            vs.append(Violation(
                "R_FUNC_LEN", rp, node.name, node.lineno, end,
                f"函数 {node.name} {length} 行，超 {limit} 行硬线", "拆成子函数",
                cfg.get("severity", "warning"),
            ))

    cfg = _cfg(rules, "R_NO_DOCSTRING")
    if cfg.get("enabled", True) and ast.get_docstring(node) is None:
        vs.append(Violation(
            "R_NO_DOCSTRING", rp, node.name, node.lineno, None,
            f"函数 {node.name} 缺 docstring", "补一句职责说明",
            cfg.get("severity", "info"),
        ))

    return vs


def _check_class(rp: str, node: ast.ClassDef, rules: dict) -> list[Violation]:
    vs: list[Violation] = []
    end = getattr(node, "end_lineno", None) or node.lineno

    cfg = _cfg(rules, "R_GOD_CLASS")
    if cfg.get("enabled", True):
        limit = cfg.get("max_methods", 15)
        methods = [n for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
        if len(methods) > limit:
            vs.append(Violation(
                "R_GOD_CLASS", rp, node.name, node.lineno, end,
                f"类 {node.name} 有 {len(methods)} 个方法，疑似上帝类", "按职责拆分类",
                cfg.get("severity", "warning"),
            ))

    cfg = _cfg(rules, "R_NO_DOCSTRING")
    if cfg.get("enabled", True) and ast.get_docstring(node) is None:
        vs.append(Violation(
            "R_NO_DOCSTRING", rp, node.name, node.lineno, None,
            f"类 {node.name} 缺 docstring", "补一句职责说明",
            cfg.get("severity", "info"),
        ))

    return vs


if __name__ == "__main__":
    import json
    import sys

    root = sys.argv[1] if len(sys.argv) > 1 else "."
    vs = analyze(root, load_rules())
    print(json.dumps([asdict(v) for v in vs], ensure_ascii=False, indent=2))
