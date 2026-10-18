"""Builder：静态扫描 + 规则引擎 → 骨架 IR（确定性阶段）。

产出**合法 IR**（可过校验器）：
- modules：按顶层目录机械分组（layer/summary/description 留空，待 WorkBuddy 补语义）
- files：每个 .py 的 docstring 首行 + 函数（name/line/end_line/signature/docstring 首行/文件内调用）
- dependencies：import 依赖（项目内文件间，确定事实）
- rule_violations：规则引擎产出，映射到函数/文件 id
- findings / flows / description：留空（语义，WorkBuddy 补）

用法：
    python -m backend.builder.builder <项目目录> [-o out.ir.json]
"""

from __future__ import annotations

import ast
import hashlib
import json
import os
import re
import sys

from backend.ir.validate import errors_only, validate
from backend.rules.engine import analyze as analyze_rules
from backend.rules.engine import analyze_from_files
from backend.rules.engine import load_rules

_SKIP_DIRS = {
    "__pycache__", ".git", ".venv", "venv", "env", "node_modules",
    "dist", "build", "tests", "test", ".idea", ".vscode", ".mypy_cache",
    ".pytest_cache", "results",
}

# 文件分类：core=核心业务 / tools=工具与支撑 / docs=文档与其他（前端分界面展示）
_CORE_TOP = {
    "agent", "contracts", "cli", "utils", "proj", "deploy",
    "formal-imo", "imo_bench_eval", "superhuman", "imo_steps",
}
_TOOL_TOP = {"tools", "scripts", "vendor", "lean-lsp-mcp", "测试工具"}
_DOC_TOP = {
    "docs", "archive", "output", "results", "logs", "data", "papers",
    "sample_data", "prompts", "题库", "题库备份", "论文实践", "测试结果",
    "与lean相关的插件", "lean-toolchain", "lean下载版",
}


def classify_path(path: str) -> str:
    """把文件相对路径分类为 core / tools / docs（供前端分界面展示）。"""
    if path.endswith((".md", ".txt", ".docx", ".pdf")):
        return "docs"
    top = path.split("/", 1)[0]
    if top in _DOC_TOP:
        return "docs"
    if top in _TOOL_TOP or top.startswith("ripgrep"):
        return "tools"
    if top in _CORE_TOP or "/" not in path:
        return "core"
    return "docs"


class IdGen:
    def __init__(self):
        self._seen: set[str] = set()

    def gen(self, base: str) -> str:
        base = sanitize(base)
        if base not in self._seen:
            self._seen.add(base)
            return base
        i = 1
        while f"{base}_{i}" in self._seen:
            i += 1
        name = f"{base}_{i}"
        self._seen.add(name)
        return name


def sanitize(s: str) -> str:
    """把任意字符串压成合法 id（字母开头，仅 [a-zA-Z0-9_-]）。"""
    out: list[str] = []
    for ch in s.lower():
        if "a" <= ch <= "z" or "0" <= ch <= "9":
            out.append(ch)
        elif ch in "-_":
            out.append("_")
        # 其余（中文/符号）丢弃，避免连续下划线
    s = "".join(out).strip("_")
    if not s:
        s = "x"
    if s[0].isdigit():
        s = "n" + s
    return s


def iter_py_files(root: str):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS and not d.startswith(".")]
        for fn in sorted(filenames):
            if fn.endswith(".py"):
                yield os.path.join(dirpath, fn)


def collect_files(root: str) -> list[dict]:
    """读取目录下全部 .py 文件为内存列表 [{path, content}]（供 /api/analyze 的 root 模式）。"""
    out: list[dict] = []
    for p in iter_py_files(root):
        rp = _rel(root, p)
        with open(p, "r", encoding="utf-8-sig") as fp:
            out.append({"path": rp, "content": fp.read()})
    return out


def _rel(root: str, path: str) -> str:
    return os.path.relpath(path, root).replace("\\", "/")


def _first_line(doc: str | None) -> str | None:
    return doc.split("\n")[0].strip() if doc else None


def _signature(lines: list[str], node: ast.AST) -> str:
    t = lines[node.lineno - 1].strip()
    return t.split("#")[0].rstrip()


def parse_source(rp: str, src: str) -> dict:
    if src.startswith("\ufeff"):
        src = src[1:]  # 去掉 UTF-8 BOM，ast.parse 不接受非打印字符
    lines = src.splitlines()
    tree = ast.parse(src)

    defined: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            defined.add(node.name)

    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                imports.append(a.name)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            imports.append(node.module)

    functions: list[dict] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        calls: set[str] = set()
        for sub in ast.walk(node):
            if isinstance(sub, ast.Call):
                name = None
                if isinstance(sub.func, ast.Name):
                    name = sub.func.id
                elif isinstance(sub.func, ast.Attribute) and isinstance(sub.func.value, ast.Name):
                    name = sub.func.attr
                if name and name in defined and name != node.name:
                    calls.add(name)
        functions.append({
            "name": node.name,
            "line": node.lineno,
            "end_line": getattr(node, "end_lineno", node.lineno),
            "signature": _signature(lines, node),
            "doc": _first_line(ast.get_docstring(node)),
            "calls": sorted(calls),
        })

    return {
        "path": rp, "lines": len(lines), "doc": _first_line(ast.get_docstring(tree)),
        "imports": sorted(set(imports)), "functions": functions,
        "hash": hashlib.md5(src.encode("utf-8")).hexdigest(),
    }


def scan_file(root: str, path: str) -> dict:
    rp = _rel(root, path)
    with open(path, "r", encoding="utf-8-sig") as fp:
        src = fp.read()
    return parse_source(rp, src)


def _resolve_import(modname: str, path_set: set[str]) -> str | None:
    """把 import 模块名解析为项目内文件路径；外部库返回 None。"""
    parts = modname.split(".")
    for i in range(len(parts), 0, -1):
        prefix = "/".join(parts[:i])
        for cand in (prefix + ".py", prefix + "/__init__.py"):
            if cand in path_set:
                return cand
    return None


README_NAMES = ("README.md", "readme.md", "README.txt", "readme.txt", "README", "readme")


def find_readme(root: str) -> str | None:
    """在项目根目录查找 README，返回其内容；没有则 None。"""
    for name in README_NAMES:
        path = os.path.join(root, name)
        if os.path.isfile(path):
            try:
                with open(path, "r", encoding="utf-8") as fp:
                    return fp.read()
            except (OSError, UnicodeDecodeError):
                continue
    return None


def extract_overview(text: str, limit: int = 800) -> str:
    """从 README 提取项目概述：去 Markdown 噪音，取有意义文本，截断。"""
    lines: list[str] = []
    in_code = False
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue
        if not line or line.startswith(("#", "![", "[![", "---", "***", "<!--")):
            continue
        line = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", line)   # 图片
        line = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", line)  # 链接保留文字
        line = line.strip("`*_>| ")
        if line:
            lines.append(line)
    text = " ".join(lines)
    if len(text) > limit:
        text = text[:limit] + "…"
    return text


def _assemble(metas: list[dict], root_name: str, violations) -> dict:
    idgen = IdGen()

    # 文件 id
    file_ids: dict[str, str] = {}
    for m in metas:
        base = m["path"].rsplit(".", 1)[0]
        file_ids[m["path"]] = idgen.gen("f_" + base)

    # 函数 id（全局唯一；用文件内序号做 key，避免同名方法如 __init__/to_dict 冲突）
    func_ids: dict[tuple[str, int], str] = {}
    for m in metas:
        for idx, fn in enumerate(m["functions"]):
            func_ids[(m["path"], idx)] = idgen.gen(
                file_ids[m["path"]] + "_" + fn["name"]
            )

    # 模块分组（顶层目录）
    groups: dict[str, list[dict]] = {}
    for m in metas:
        parts = m["path"].split("/")
        key = parts[0] if len(parts) > 1 else "__root__"
        groups.setdefault(key, []).append(m)

    modules: list[dict] = []
    path_to_module: dict[str, str] = {}
    for key in sorted(groups):
        label = root_name if key == "__root__" else key
        mid = idgen.gen("m_" + label)
        cat = classify_path(groups[key][0]["path"])
        modules.append({
            "id": mid, "label": label, "category": cat,
            "files": [file_ids[m["path"]] for m in groups[key]],
        })
        for m in groups[key]:
            path_to_module[m["path"]] = mid

    # files
    files: list[dict] = []
    id_to_path: dict[str, str] = {}
    for m in metas:
        fid = file_ids[m["path"]]
        id_to_path[fid] = m["path"]
        files.append({
            "id": fid, "path": m["path"], "module": path_to_module[m["path"]],
            "language": "python", "lines": m["lines"], "summary": m["doc"],
            "hash": m.get("hash"), "category": classify_path(m["path"]),
            "functions": [
                {
                    "id": func_ids[(m["path"], idx)],
                    "name": fn["name"], "line": fn["line"], "end_line": fn["end_line"],
                    "signature": fn["signature"], "summary": fn["doc"],
                }
                for idx, fn in enumerate(m["functions"])
            ],
        })

    # 函数调用（文件内，映射为 id）
    for m in metas:
        fid = file_ids[m["path"]]
        fe = next(f for f in files if f["id"] == fid)
        by_name = {fn["name"]: fn for fn in fe["functions"]}
        for fn in fe["functions"]:
            meta_fn = next(x for x in m["functions"] if x["name"] == fn["name"])
            call_ids = []
            for cname in meta_fn["calls"]:
                if cname in by_name:
                    call_ids.append(by_name[cname]["id"])
            fn["calls"] = sorted(set(call_ids))
            fn["called_by"] = []
    # 反推 called_by
    for fe in files:
        for fn in fe["functions"]:
            for cid in fn.get("calls", []):
                for fe2 in files:
                    for fn2 in fe2["functions"]:
                        if fn2["id"] == cid and fn["id"] not in fn2["called_by"]:
                            fn2["called_by"].append(fn["id"])

    # dependencies（import 匹配）
    path_set = set(file_ids.keys())
    deps: list[dict] = []
    for m in metas:
        for imp in m["imports"]:
            target = _resolve_import(imp, path_set)
            if target and target != m["path"]:
                deps.append({
                    "from": file_ids[m["path"]], "to": file_ids[target], "type": "import",
                })

    # rule_violations（映射 node，按函数起始行精确匹配，避免同名方法歧义）
    line_to_func: dict[tuple[str, int], str] = {}
    for m in metas:
        for idx, fn in enumerate(m["functions"]):
            line_to_func[(m["path"], fn["line"])] = func_ids[(m["path"], idx)]

    rvs: list[dict] = []
    for v in violations:
        node = None
        if v.name and v.line and (v.path, v.line) in line_to_func:
            node = line_to_func[(v.path, v.line)]
        elif v.path in file_ids:
            node = file_ids[v.path]
        if node:
            rvs.append({
                "id": idgen.gen("v"), "rule": v.rule, "node": node,
                "line": v.line, "detail": v.detail, "suggestion": v.suggestion,
                "severity": v.severity,
            })

    # module_dependencies（文件依赖聚合）
    mod_deps: list[dict] = []
    seen_md: set[tuple[str, str]] = set()
    for d in deps:
        fm = path_to_module[id_to_path[d["from"]]]
        tm = path_to_module[id_to_path[d["to"]]]
        if fm != tm and (fm, tm) not in seen_md:
            seen_md.add((fm, tm))
            mod_deps.append({"from": fm, "to": tm, "type": "import"})

    ir = {
        "schema_version": 2,
        "meta": {
            "project": root_name, "language": "python", "generated_by": "builder",
            "rules_version": "1.0",
            "stats": {
                "files": len(files), "lines": sum(f["lines"] for f in files),
                "functions": sum(len(f["functions"]) for f in files),
                "errors": 0, "warnings": len(rvs),
            },
        },
        "modules": modules,
        "files": files,
        "dependencies": deps,
        "module_dependencies": mod_deps,
        "flows": [],
        "rule_violations": rvs,
        "findings": [],
    }
    return ir


def build_ir(root: str) -> dict:
    root = os.path.abspath(root)
    root_name = os.path.basename(root.rstrip("/\\")) or "project"
    metas: list[dict] = []
    for p in iter_py_files(root):
        try:
            metas.append(scan_file(root, p))
        except (SyntaxError, UnicodeDecodeError):
            continue  # 单个文件解析失败不中断整个项目
    metas.sort(key=lambda m: m["path"])
    if not metas:
        raise ValueError(f"目录下没有可解析的 .py 文件：{root}")
    violations = analyze_rules(root, load_rules())
    ir = _assemble(metas, root_name, violations)
    readme = find_readme(root)
    if readme:
        ir["meta"]["overview"] = extract_overview(readme)
    return ir


def build_ir_from_files(files: list[dict], project_name: str = "project", readme: str | None = None) -> dict:
    """从内存文件列表构建 IR（files = [{path, content}]）。

    供「前端点选文件夹 → 上传文件内容」场景使用，后端无需读磁盘。
    readme 为项目根目录 README 内容（可选），用于生成项目概述。
    """
    metas = []
    for f in files:
        try:
            metas.append(parse_source(f["path"], f["content"]))
        except SyntaxError:
            continue
    metas.sort(key=lambda m: m["path"])
    if not metas:
        raise ValueError("没有可解析的 .py 文件")
    violations = analyze_from_files(files, load_rules())
    ir = _assemble(metas, project_name, violations)
    if readme:
        ir["meta"]["overview"] = extract_overview(readme)
    return ir


ENRICH_FILENAME = "enrich.ir.json"


def load_or_build_ir(root: str) -> tuple[dict, str]:
    """优先加载语义填充后的 enrich.ir.json，否则回退骨架 IR。

    返回 (IR, 来源)；来源 = "enriched" 或 "skeleton"。
    语义填充（layer/summary/description/findings/flows）由 WorkBuddy 完成，
    产物写入 <root>/enrich.ir.json；本函数是「机器骨架 ↔ LLM 语义」的衔接点。
    """
    root = os.path.abspath(root)
    enrich_path = os.path.join(root, ENRICH_FILENAME)
    if os.path.isfile(enrich_path):
        try:
            with open(enrich_path, "r", encoding="utf-8") as fp:
                ir = json.load(fp)
            if not errors_only(validate(ir)):
                return ir, "enriched"
        except (json.JSONDecodeError, OSError):
            pass  # 坏文件回退骨架
    return build_ir(root), "skeleton"


def main(argv: list[str]) -> int:
    root = argv[0] if argv else "."
    out_path = None
    if "-o" in argv:
        i = argv.index("-o")
        if i + 1 < len(argv):
            out_path = argv[i + 1]
    ir = build_ir(root)
    issues = [i for i in validate(ir) if i.is_error]
    if issues:
        print("⚠ 骨架 IR 校验未通过：", file=sys.stderr)
        for i in issues:
            print("  " + str(i), file=sys.stderr)
        return 1
    text = json.dumps(ir, ensure_ascii=False, indent=2)
    if out_path:
        with open(out_path, "w", encoding="utf-8") as fp:
            fp.write(text)
        print(f"已写出 {out_path}")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
