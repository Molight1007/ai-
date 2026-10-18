"""LLM 客户端（OpenAI 兼容端点，零第三方依赖，标准库 urllib）。

支持 DeepSeek / OpenAI / 任意 OpenAI 兼容网关（含本地 Ollama 的 /v1 端点）。
配置：backend/llm.toml（优先，从 llm.toml.example 复制）；api_key 也可用环境变量 LLM_API_KEY。
"""

from __future__ import annotations

import json
import os
import tomllib
import urllib.error
import urllib.request

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "llm.toml")

_DEFAULTS = {
    "base_url": "https://api.deepseek.com",
    "model": "deepseek-chat",
    "api_key": "",
    "timeout": 180,
}


def load_config() -> dict:
    cfg = dict(_DEFAULTS)
    if os.path.isfile(CONFIG_PATH):
        with open(CONFIG_PATH, "rb") as fp:
            cfg.update(tomllib.load(fp).get("llm", {}))
    cfg["api_key"] = cfg.get("api_key") or os.environ.get("LLM_API_KEY", "")
    return cfg


def has_key() -> bool:
    """是否已配置 API Key（供前端显示 AI 增强可用性）。"""
    return bool(load_config().get("api_key"))


def save_config(cfg: dict) -> None:
    """把配置写回 llm.toml（tomllib 只读，这里手写序列化）。"""
    lines = ["[llm]"]
    for key in ("base_url", "model", "api_key"):
        lines.append(f'{key} = "{cfg.get(key, "")}"')
    with open(CONFIG_PATH, "w", encoding="utf-8") as fp:
        fp.write("\n".join(lines) + "\n")


def chat(messages: list[dict], config: dict | None = None) -> str:
    """调用 chat completions，返回助手回复文本。"""
    cfg = config or load_config()
    if not cfg.get("api_key"):
        raise RuntimeError(
            "未配置 API Key：复制 backend/llm.toml.example 为 backend/llm.toml 并填入，"
            "或设置环境变量 LLM_API_KEY"
        )
    base = str(cfg["base_url"]).rstrip("/")
    url = base + "/chat/completions"
    payload = {
        "model": cfg["model"],
        "messages": messages,
        "temperature": 0.2,
        "stream": False,
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {cfg['api_key']}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=int(cfg.get("timeout", 180))) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        # 透传大模型 API 的真实错误（key 无效 / 模型名不存在等），不吞成 "HTTP 400"
        body = e.read().decode("utf-8", "replace")
        msg = body[:300]
        try:
            err = json.loads(body)
            if isinstance(err.get("error"), dict):
                msg = err["error"].get("message") or msg
            elif err.get("error"):
                msg = str(err["error"])
        except Exception:
            pass
        raise RuntimeError(f"大模型 API 返回错误（HTTP {e.code}）：{msg}") from e
    return data["choices"][0]["message"]["content"]
