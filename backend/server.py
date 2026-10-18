"""轻量 HTTP server：把 Builder 串成后端接口。零第三方依赖（标准库 http.server）。

接口：
    GET /api/ir         → 扫描 PROJECT_ROOT，返回骨架 IR（JSON）
    GET /api/file?path= → 读 PROJECT_ROOT 下的源码（相对路径），返回 JSON
    GET /api/health     → 健康检查

用法：
    python -m backend.server [项目目录] [--port 8000]
    默认项目目录 = 环境变量 PROJECT_ROOT 或当前目录。

说明：原设计文档写 FastAPI，实际改用标准库 http.server —— 两个 GET 接口用不上
FastAPI 的生态，且零依赖规避 Python 3.14 下 pydantic-core wheel 兼容风险。
"""

from __future__ import annotations

import json
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from backend.builder.builder import build_ir_from_files, load_or_build_ir
from backend.enrich import enrich
from backend.llm import load_config, save_config

PROJECT_ROOT = os.path.abspath(os.environ.get("PROJECT_ROOT", "."))


def safe_join(root: str, rel: str) -> str | None:
    """把相对路径安全地解析到 root 内；越界返回 None。"""
    base = os.path.abspath(root)
    target = os.path.abspath(os.path.join(base, rel))
    if target == base or target.startswith(base + os.sep):
        return target
    return None


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        if path == "/api/health":
            self._json({"ok": True, "root": PROJECT_ROOT})
        elif path == "/api/llm/status":
            cfg = load_config()
            self._json({
                "configured": bool(cfg.get("api_key")),
                "model": cfg.get("model"),
                "base_url": cfg.get("base_url"),
            })
        elif path == "/api/ir":
            self._ir(query.get("root", [PROJECT_ROOT])[0])
        elif path == "/api/file":
            self._file(query.get("root", [PROJECT_ROOT])[0], query.get("path", [""])[0])
        else:
            self._json({"error": "not found"}, 404)

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/analyze":
            self._analyze()
        elif parsed.path == "/api/enrich":
            self._enrich()
        elif parsed.path == "/api/llm/config":
            self._llm_config()
        elif parsed.path == "/api/shutdown":
            self._shutdown()
        else:
            self._json({"error": "not found"}, 404)

    def _llm_config(self):
        try:
            data = self._read_body()
            api_key = str(data.get("api_key", "")).strip()
            if not api_key:
                self._json({"error": "api_key 不能为空"}, 400)
                return
            cfg = load_config()
            cfg["api_key"] = api_key
            if data.get("model"):
                cfg["model"] = data["model"]
            if data.get("base_url"):
                cfg["base_url"] = data["base_url"]
            save_config(cfg)
            self._json({"ok": True, "configured": True})
        except Exception as e:  # noqa: BLE001
            self._json({"error": str(e)}, 500)

    def _read_body(self) -> dict:
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length) if length else b"{}"
        return json.loads(body.decode("utf-8"))

    def _analyze(self):
        try:
            data = self._read_body()
            ir = build_ir_from_files(
                data.get("files", []), data.get("project", "project"),
                readme=data.get("readme"),
            )
            self._json(ir)
        except Exception as e:  # noqa: BLE001 —— 接口要兜底返回错误
            self._json({"error": str(e)}, 500)

    def _enrich(self):
        try:
            data = self._read_body()
            files = data.get("files", [])
            ir = build_ir_from_files(
                files, data.get("project", "project"), readme=data.get("readme"),
            )
            file_contents = {f["path"]: f["content"] for f in files}
            ir = enrich(ir, file_contents)
            self._json(ir)
        except Exception as e:  # noqa: BLE001 —— 接口要兜底返回错误
            self._json({"error": str(e)}, 500)

    def _shutdown(self):
        self._json({"ok": True, "message": "server shutting down"})
        # 先返回响应，再关闭 server（新线程，避免阻塞当前请求）
        threading.Thread(target=self.server.shutdown, daemon=True).start()

    def _ir(self, root: str):
        try:
            ir, _source = load_or_build_ir(root)
            self._json(ir)
        except Exception as e:  # noqa: BLE001 —— 接口要兜底返回错误
            self._json({"error": str(e)}, 500)

    def _file(self, root: str, rel: str):
        if not rel:
            self._json({"error": "missing path"}, 400)
            return
        target = safe_join(root, rel)
        if target is None or not os.path.isfile(target):
            self._json({"error": "file not found"}, 404)
            return
        with open(target, "r", encoding="utf-8") as fp:
            content = fp.read()
        self._json({"path": rel, "content": content})

    def _json(self, obj, status: int = 200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):  # 静默访问日志
        pass


def main(argv: list[str]) -> int:
    global PROJECT_ROOT
    root = PROJECT_ROOT
    port = int(os.environ.get("PORT", "8000"))
    i = 0
    while i < len(argv):
        if argv[i] == "--port" and i + 1 < len(argv):
            port = int(argv[i + 1])
            i += 2
        else:
            root = os.path.abspath(argv[i])
            i += 1
    PROJECT_ROOT = root
    print(f"AI 代码可视化 server: http://127.0.0.1:{port}  (root={root})")
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
