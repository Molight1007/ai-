"""IR schema v2 —— 校验器。

输入：dict（通常来自 project.ir.json）。
输出：Issue 列表（规则码 + 人类可读消息 + 定位路径）。

设计要点（沿用 agent-flow-diagram 的「规则码」理念）：
- 校验失败给规则码而非堆栈，改 IR 时按码局部修。
- 每条引用都必须指向已声明的节点（悬空引用必拦），杜绝 LLM 发明拓扑。

用法：
    from backend.ir.validate import validate
    issues = validate(ir_dict)
    errors = [i for i in issues if i.is_error]
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from . import schema as S

_ID_RE = re.compile(S.ID_RE)


@dataclass
class Issue:
    code: str
    message: str
    path: str = ""
    is_error: bool = True

    def __str__(self) -> str:  # pragma: no cover - 仅展示
        loc = f" @ {self.path}" if self.path else ""
        return f"[{self.code}] {self.message}{loc}"


def _fmt_path(base: str, *parts) -> str:
    """拼出定位路径，如 modules[0].id 或 files[2].functions[0].line。"""
    return base + "".join(f"[{p}]" if isinstance(p, int) else f".{p}" for p in parts)


def validate(ir) -> list[Issue]:
    """校验一份 IR，返回全部 Issue（空列表 = 通过）。"""
    issues: list[Issue] = []

    if not isinstance(ir, dict):
        return [Issue("IR/BAD_TYPE", "IR 根节点必须是对象", "")]

    # 1) 顶层必填 + 版本
    for key in S.REQUIRED_TOP:
        if key not in ir:
            issues.append(Issue("IR/MISSING_KEY", f"顶层缺少必填字段 {key}", key))
    if "schema_version" in ir:
        try:
            if int(ir["schema_version"]) != S.SCHEMA_VERSION:
                issues.append(
                    Issue("IR/BAD_VERSION",
                          f"schema_version 应为 {S.SCHEMA_VERSION}，实际 {ir['schema_version']}",
                          "schema_version")
                )
        except (TypeError, ValueError):
            issues.append(Issue("IR/BAD_TYPE", "schema_version 必须为整数", "schema_version"))

    # 2) meta
    if isinstance(ir.get("meta"), dict):
        for key in S.REQUIRED_META:
            if key not in ir["meta"]:
                issues.append(
                    Issue("IR/MISSING_KEY", f"meta 缺少字段 {key}", f"meta.{key}"))
    else:
        issues.append(Issue("IR/MISSING_KEY", "缺少 meta 对象", "meta"))

    # 3) 收集节点 id，检查重复
    seen_ids: dict[str, str] = {}  # id -> kind
    def _declare(node_id, kind, path):
        if not isinstance(node_id, str) or not _ID_RE.match(node_id):
            issues.append(
                Issue("IR/BAD_ID", f"id 非法（应匹配 {S.ID_RE}）：{node_id!r}", path))
            return
        if node_id in seen_ids:
            issues.append(
                Issue("IR/DUPLICATE_ID",
                      f"id 重复：{node_id} 已作为 {seen_ids[node_id]} 声明", path))
        else:
            seen_ids[node_id] = kind

    modules = ir.get("modules")
    files = ir.get("files")

    # 4) modules
    if isinstance(modules, list):
        if not modules:
            issues.append(Issue("IR/EMPTY_COLLECTION", "modules 不能为空", "modules"))
        for i, m in enumerate(modules):
            base = f"modules[{i}]"
            if not isinstance(m, dict):
                issues.append(Issue("IR/BAD_TYPE", "模块必须是对象", base)); continue
            for key in S.REQUIRED_MODULE:
                if key not in m:
                    issues.append(Issue("IR/MISSING_KEY", f"模块缺少 {key}", f"{base}.{key}"))
            if "id" in m:
                _declare(m["id"], "module", f"{base}.id")
            if "layer" in m and m["layer"] not in S.LAYERS:
                issues.append(Issue("IR/BAD_LAYER",
                                    f"layer 非法（应在 {S.LAYERS}）：{m['layer']!r}", f"{base}.layer"))
            if "files" in m:
                if not isinstance(m["files"], list):
                    issues.append(Issue("IR/BAD_TYPE", "module.files 必须是数组", f"{base}.files"))
                else:
                    for j, f in enumerate(m["files"]):
                        if not isinstance(f, str):
                            issues.append(Issue("IR/BAD_TYPE",
                                                "module.files 元素必须是字符串", f"{base}.files[{j}]"))
    elif modules is not None:
        issues.append(Issue("IR/BAD_TYPE", "modules 必须是数组", "modules"))

    # 5) files + functions
    if isinstance(files, list):
        if not files:
            issues.append(Issue("IR/EMPTY_COLLECTION", "files 不能为空", "files"))
        for i, f in enumerate(files):
            base = f"files[{i}]"
            if not isinstance(f, dict):
                issues.append(Issue("IR/BAD_TYPE", "文件必须是对象", base)); continue
            for key in S.REQUIRED_FILE:
                if key not in f:
                    issues.append(Issue("IR/MISSING_KEY", f"文件缺少 {key}", f"{base}.{key}"))
            if "id" in f:
                _declare(f["id"], "file", f"{base}.id")
            if "module" in f and modules is not None:
                # 悬空模块引用（延迟到模块 id 收集后统一校验，见下方）
                pass
            if "lines" in f:
                if not isinstance(f["lines"], int) or f["lines"] < 0:
                    issues.append(Issue("IR/BAD_LINE",
                                        "lines 必须为 >=0 的整数", f"{base}.lines"))
            for j, fn in enumerate(f.get("functions") or []):
                fb = f"{base}.functions[{j}]"
                if not isinstance(fn, dict):
                    issues.append(Issue("IR/BAD_TYPE", "函数必须是对象", fb)); continue
                for key in S.REQUIRED_FUNCTION:
                    if key not in fn:
                        issues.append(Issue("IR/MISSING_KEY", f"函数缺少 {key}", f"{fb}.{key}"))
                if "id" in fn:
                    _declare(fn["id"], "function", f"{fb}.id")
                _check_line(issues, fn, fb)
                for lst in ("calls", "called_by"):
                    _check_id_list(issues, fn.get(lst), f"{fb}.{lst}")
    elif files is not None:
        issues.append(Issue("IR/BAD_TYPE", "files 必须是数组", "files"))

    # 6) 模块引用（files[].module 必须指向已声明模块）
    if isinstance(modules, list) and isinstance(files, list):
        module_ids = {m["id"] for m in modules if isinstance(m, dict) and "id" in m}
        for i, f in enumerate(files):
            if isinstance(f, dict) and "module" in f:
                if f["module"] not in module_ids:
                    issues.append(Issue("IR/DANGLING_MODULE",
                                        f"文件引用了不存在的模块：{f['module']!r}",
                                        f"files[{i}].module"))
            if isinstance(f, dict) and "functions" in f:
                pass  # 函数级引用在下方统一处理

    # 7) module_dependencies（模块级聚合边）
    for i, d in enumerate(ir.get("module_dependencies") or []):
        base = f"module_dependencies[{i}]"
        if not isinstance(d, dict):
            issues.append(Issue("IR/BAD_TYPE", "module_dependencies 元素必须是对象", base)); continue
        for key in S.REQUIRED_MODDEP:
            if key not in d:
                issues.append(Issue("IR/MISSING_KEY", f"模块依赖缺少 {key}", f"{base}.{key}"))
        _check_dep_ends(issues, d, base, valid=seen_ids, kind="module")

    # 8) dependencies（文件/函数间依赖）
    for i, d in enumerate(ir.get("dependencies") or []):
        base = f"dependencies[{i}]"
        if not isinstance(d, dict):
            issues.append(Issue("IR/BAD_TYPE", "dependencies 元素必须是对象", base)); continue
        for key in S.REQUIRED_DEP:
            if key not in d:
                issues.append(Issue("IR/MISSING_KEY", f"依赖缺少 {key}", f"{base}.{key}"))
        _check_dep_ends(issues, d, base, valid=seen_ids, kind="node")

    # 9) flows（主流程调用链）
    for i, fl in enumerate(ir.get("flows") or []):
        base = f"flows[{i}]"
        if not isinstance(fl, dict):
            issues.append(Issue("IR/BAD_TYPE", "flows 元素必须是对象", base)); continue
        for key in S.REQUIRED_FLOW:
            if key not in fl:
                issues.append(Issue("IR/MISSING_KEY", f"flow 缺少 {key}", f"{base}.{key}"))
        if "steps" in fl:
            _check_id_list(issues, fl["steps"], f"{base}.steps")

    # 10) rule_violations
    for i, v in enumerate(ir.get("rule_violations") or []):
        base = f"rule_violations[{i}]"
        if not isinstance(v, dict):
            issues.append(Issue("IR/BAD_TYPE", "rule_violations 元素必须是对象", base)); continue
        for key in S.REQUIRED_VIOLATION:
            if key not in v:
                issues.append(Issue("IR/MISSING_KEY", f"违规缺少 {key}", f"{base}.{key}"))
        if "id" in v and isinstance(v["id"], str) and v["id"]:
            _declare(v["id"], "rule_violation", f"{base}.id")

    # 11) findings
    for i, f in enumerate(ir.get("findings") or []):
        base = f"findings[{i}]"
        if not isinstance(f, dict):
            issues.append(Issue("IR/BAD_TYPE", "findings 元素必须是对象", base)); continue
        for key in S.REQUIRED_FINDING:
            if key not in f:
                issues.append(Issue("IR/MISSING_KEY", f"finding 缺少 {key}", f"{base}.{key}"))
        if "id" in f and isinstance(f["id"], str) and f["id"]:
            _declare(f["id"], "finding", f"{base}.id")
        if "severity" in f and f["severity"] not in S.SEVERITIES:
            issues.append(Issue("IR/BAD_SEVERITY",
                                f"severity 非法（应在 {S.SEVERITIES}）：{f['severity']!r}",
                                f"{base}.severity"))

    # 12) 引用完整性：findings/rule_violations/dependencies/flows 的 node/from/to/steps/calls
    _check_refs(issues, ir, seen_ids)

    return issues


def _check_line(issues, obj, base):
    line = obj.get("line")
    end = obj.get("end_line")
    if line is not None and (not isinstance(line, int) or line < 1):
        issues.append(Issue("IR/BAD_LINE", "line 必须为 >=1 的整数", f"{base}.line"))
    if end is not None and (not isinstance(end, int) or end < 1):
        issues.append(Issue("IR/BAD_LINE", "end_line 必须为 >=1 的整数", f"{base}.end_line"))
    if (isinstance(line, int) and isinstance(end, int) and end < line):
        issues.append(Issue("IR/BAD_LINE", "end_line 不能小于 line", f"{base}.end_line"))


def _check_id_list(issues, val, base):
    if val is None:
        return
    if not isinstance(val, list):
        issues.append(Issue("IR/BAD_TYPE", f"{base} 必须是数组", base)); return
    for j, x in enumerate(val):
        if not isinstance(x, str):
            issues.append(Issue("IR/BAD_TYPE", f"{base}[{j}] 必须是字符串", f"{base}[{j}]"))


def _check_dep_ends(issues, d, base, valid, kind):
    for end in ("from", "to"):
        ref = d.get(end)
        if ref is None:
            continue
        if not isinstance(ref, str):
            issues.append(Issue("IR/BAD_TYPE", f"依赖 {end} 必须是字符串", f"{base}.{end}")); continue
        if ref not in valid:
            issues.append(Issue("IR/DANGLING_REF",
                                f"依赖 {end} 引用了未声明的{kind}：{ref!r}", f"{base}.{end}"))


def _check_refs(issues, ir, seen_ids):
    """引用完整性：所有指向节点 id 的字段，其值必须已声明。"""
    # findings.node / rule_violations.node
    for coll, code in (("findings", "IR/DANGLING_NODE"), ("rule_violations", "IR/DANGLING_NODE")):
        for i, item in enumerate(ir.get(coll) or []):
            if not isinstance(item, dict):
                continue
            node = item.get("node")
            if node is not None and (not isinstance(node, str) or node not in seen_ids):
                issues.append(Issue(code, f"{coll} 引用了未声明的节点：{node!r}",
                                    f"{coll}[{i}].node"))
    # modules[].files 必须指向已声明 file
    for i, m in enumerate(ir.get("modules") or []):
        if not isinstance(m, dict) or not isinstance(m.get("files"), list):
            continue
        for j, fid in enumerate(m["files"]):
            if isinstance(fid, str) and fid not in seen_ids:
                issues.append(Issue("IR/DANGLING_FILE",
                                    f"模块引用了未声明的文件：{fid!r}", f"modules[{i}].files[{j}]"))
    # flows[].steps 与 functions[].calls/called_by 必须指向已声明节点
    for i, fl in enumerate(ir.get("flows") or []):
        if not isinstance(fl, dict) or not isinstance(fl.get("steps"), list):
            continue
        for j, s in enumerate(fl["steps"]):
            if isinstance(s, str) and s not in seen_ids:
                issues.append(Issue("IR/DANGLING_NODE",
                                    f"flow 步骤引用了未声明的节点：{s!r}", f"flows[{i}].steps[{j}]"))
    for i, f in enumerate(ir.get("files") or []):
        if not isinstance(f, dict):
            continue
        for j, fn in enumerate(f.get("functions") or []):
            if not isinstance(fn, dict):
                continue
            for lst in ("calls", "called_by"):
                arr = fn.get(lst)
                if not isinstance(arr, list):
                    continue
                for k, ref in enumerate(arr):
                    if isinstance(ref, str) and ref not in seen_ids:
                        issues.append(Issue("IR/DANGLING_NODE",
                                            f"函数引用未声明的节点：{ref!r}",
                                            f"files[{i}].functions[{j}].{lst}[{k}]"))


def errors_only(issues: list[Issue]) -> list[Issue]:
    return [i for i in issues if i.is_error]
