"""语义填充：用 LLM 给骨架 IR 补 layer / summary / description / findings / flows。

骨架 IR（Builder 产出）只含结构事实；本模块调 LLM 补语义，得到「功能视图 / 审查模式」
所需的完整信息。校验不通过则抛错，不产出半成品。

LLM 只被要求「引用给定 id」，不发明拓扑；返回的补丁经校验器兜底。
"""

from __future__ import annotations

import json
import re

from backend.ir.validate import errors_only, validate
from backend.llm import chat

SYSTEM_PROMPT = """你是一名代码架构分析专家。给定一个 Python 项目的骨架信息（模块/文件/函数及其 docstring）和关键源码，为项目补全语义信息。

只输出一个 JSON 对象（不要任何解释、不要 markdown 代码块标记），结构如下：
{
  "modules": [{"id": "模块id", "layer": "L0-L5", "summary": "一句话职责", "description": "详细功能说明"}],
  "files": [{"id": "文件id", "description": "详细功能说明"}],
  "findings": [{"severity": "error|warning|info", "node": "函数或文件id", "line": 行号, "title": "问题标题", "detail": "详情", "suggestion": "修复建议"}],
  "flows": [{"label": "主流程名", "steps": ["函数id1", "函数id2"]}]
}

规则：
- 结合「项目概述（README）」理解项目定位，据此划分模块、写出准确的 summary/description
- 只引用骨架里给出的 id，绝不发明新 id
- layer 取值：L0 纯算法 / L1 工具 / L2 业务 / L3 契约 / L4 编排 / L5 入口
- findings 只报告确定或高度可疑的 bug（逻辑错误、边界遗漏、资源泄漏等），不要泛泛而谈风格问题
- flows 描述核心调用链，steps 按调用顺序给出函数 id
- 用中文书写 summary / description / title / detail / suggestion"""


def enrich(ir: dict, file_contents: dict[str, str] | None = None) -> dict:
    """对骨架 IR 做语义填充，返回 enrich 后的 IR（原 IR 不修改）。"""
    ir = json.loads(json.dumps(ir))  # 深拷贝，避免污染调用方
    reply = chat([
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": _build_prompt(ir, file_contents or {})},
    ])
    patch = _parse_json(reply)
    _apply_patch(ir, patch)
    errors = errors_only(validate(ir))
    if errors:
        raise ValueError("LLM 语义填充产物未通过校验：" + "; ".join(str(e) for e in errors[:5]))
    ir["meta"]["generated_by"] = ir["meta"].get("generated_by", "llm") + "+llm"
    return ir


def _build_prompt(ir: dict, file_contents: dict[str, str]) -> str:
    lines = [f"项目名：{ir['meta']['project']}\n"]
    lines.append(f"项目概述（README）：{ir['meta'].get('overview', '（无 README，请根据代码自行判断）')}")
    lines.append("")
    lines.append("模块：")
    for m in ir["modules"]:
        lines.append(f"- {m['id']} label={m['label']}")
    lines.append("\n文件与函数：")
    for f in ir["files"]:
        lines.append(f"- {f['id']} path={f['path']} doc={f.get('summary') or ''}")
        for fn in f.get("functions", []):
            lines.append(f"    {fn['id']} name={fn['name']} doc={fn.get('summary') or ''}")
    lines.append("\n关键源码（截断）：")
    for path, content in file_contents.items():
        lines.append(f"=== {path} ===")
        lines.append(content[:3000])
    return "\n".join(lines)


def _parse_json(reply: str) -> dict:
    """从 LLM 回复提取 JSON（容忍 ```json 包裹与前后杂讯）。"""
    text = reply.strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    if fence:
        text = fence.group(1).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("LLM 未返回 JSON")
    return json.loads(text[start:end + 1])


def _apply_patch(ir: dict, patch: dict) -> None:
    modules = {m["id"]: m for m in ir["modules"]}
    for p in patch.get("modules", []):
        m = modules.get(p.get("id"))
        if not m:
            continue
        if p.get("layer") in ("L0", "L1", "L2", "L3", "L4", "L5"):
            m["layer"] = p["layer"]
        if p.get("summary"):
            m["summary"] = p["summary"]
        if p.get("description"):
            m["description"] = p["description"]

    files = {f["id"]: f for f in ir["files"]}
    for p in patch.get("files", []):
        f = files.get(p.get("id"))
        if f and p.get("description"):
            f["description"] = p["description"]

    valid_nodes = {m["id"] for m in ir["modules"]} | {f["id"] for f in ir["files"]}
    for f in ir["files"]:
        valid_nodes |= {fn["id"] for fn in f.get("functions", [])}

    n = len(ir.get("findings", []))
    for p in patch.get("findings", []):
        if p.get("node") not in valid_nodes:
            continue
        n += 1
        ir.setdefault("findings", []).append({
            "id": f"F{n}", "severity": p.get("severity", "warning"),
            "type": "llm", "node": p["node"], "line": p.get("line"),
            "title": p.get("title", "问题"), "detail": p.get("detail"),
            "suggestion": p.get("suggestion"),
        })

    for p in patch.get("flows", []):
        steps = [s for s in p.get("steps", []) if s in valid_nodes]
        if len(steps) >= 2:
            ir.setdefault("flows", []).append({
                "id": f"flow_{len(ir.get('flows', []))}", "label": p.get("label", "主流程"),
                "steps": steps,
            })
