"""LLM 客户端（OpenAI 兼容端点，零第三方依赖，标准库 urllib）。

支持 DeepSeek / OpenAI / 任意 OpenAI 兼容网关（含本地 Ollama 的 /v1 端点）。
配置：backend/llm.toml（优先，从 llm.toml.example 复制）；api_key 也可用环境变量 LLM_API_KEY。
"""

from __future__ import annotations

import json
import os
import tomllib
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
    with urllib.request.urlopen(req, timeout=int(cfg.get("timeout", 180))) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data["choices"][0]["message"]["content"]
