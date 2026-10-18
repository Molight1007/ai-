# AI Code Visualizer

把 **AI 生成的代码**变成一张可交互的图：先看懂结构，再自动指出 bug 与规范问题，辅助你定位修改。

它是程序员打开 AI 代码的「**阅读器 + 体检报告**」：

```
打开 AI 代码 → 可视化结构（看懂） → 自审核（指出 bug/违规） → 点进去改
```

## 核心设计：构建与展示分离

```
LLM（非确定，谁都能当）──产出──▶ 类型化 IR（唯一契约）──渲染──▶ 确定性 Viewer（纯前端）
```

- **构建** = 读代码 + 大模型分析 → 产出 `IR`（JSON）。静态部分（结构/违规）由 Python 机器确定性完成；语义部分（职责/功能/bug）由任意 LLM（含 WorkBuddy）补。
- **展示** = 把 IR 确定性渲染成交互界面，不需要 LLM，可离线、可重跑。

## 三个视图

| 视图 | 内容 |
|---|---|
| **代码方面** | 模块 → 文件 → 源码，逐层下钻，点文件在当前界面内打开代码 |
| **功能方面** | 同结构，但讲「这模块/函数是干嘛的」，不展示代码 |
| **审查模式** | 风险角标 + 问题清单，点一条跳转到源码行 |

交互：**图即文件夹** —— 项目总图（模块）→ 点模块进文件图 → 点文件看代码，面包屑任意级返回。

## 快速开始

**一键启动**（Windows 双击 `start.bat`，或命令行）：

```bash
python start.py
```

脚本会自动完成：安装前端依赖（首次）→ 启动后端 → 启动前端 → 打开浏览器。

手动启动（两步）：

```bash
python -m backend.server --port 8000        # 后端（零第三方依赖）
cd frontend && npm install && npm run dev   # 前端（Node 22+）
```

前端经 vite proxy（`/api` → `:8000`）取真实数据；后端未启动时自动回退到内置示例数据。

## AI 语义填充（单一分析通道）

工具是**单一通道**：点一下按钮，自动完成「审核文件 → 定位代码板块 → 生成架构图」。

内部流程：
1. 程序静态扫描（AST）：抽模块/文件/函数/依赖 + 规则违规（机器确定）
2. 大模型按 **README 概述** 定位 AI 代码板块，补 `layer` / `summary` / `description` / `findings` / `flows`
3. 校验器兜底，产出一份完整架构图

配置 DeepSeek（前端输入框直接保存，或手动）：

```toml
# backend/llm.toml（从 llm.toml.example 复制）
[llm]
base_url = "https://api.deepseek.com"
model = "deepseek-chat"
api_key = "sk-你的key"
```

支持任意 OpenAI 兼容端点（OpenAI / DeepSeek / 本地 Ollama 的 `/v1`）。

## 前端操作

1. 首次：输入 DeepSeek API Key 并保存（存本地，不提交）
2. 点「选择文件夹生成架构图」→ 自动出完整图（结构 + 功能 + bug 审查）
3. 「终止服务」一键关停后端

## 规则引擎（自审核的「机器确定」一半）

规则在 `backend/rules/code-rules.toml`，可配置、可扩展：

| 规则 | 阈值 | 说明 |
|---|---|---|
| `R_FUNC_LEN` | 150 行 | 函数超长 |
| `R_FILE_LEN` | 800 行 | 文件超长 |
| `R_GOD_CLASS` | 15 方法 | 疑似上帝类 |
| `R_NO_DOCSTRING` | — | 缺职责说明 |
| `R_BARE_EXCEPT` | — | 裸 except |

语义 bug（逻辑错误、边界遗漏等）由 LLM 产出 `findings`，标「可疑 + 需复核」，与机器违规分开展示。

## 项目结构

```
backend/
  ir/          # IR 契约 v2 + 校验器（规则码）
  rules/       # 规则引擎（ast + tomllib）
  builder/     # 静态扫描 → 骨架 IR（+ enrich 衔接）
  llm.py       # LLM 客户端（OpenAI 兼容，标准库 urllib）
  enrich.py    # 语义填充（LLM → 语义 IR，校验兜底）
  server.py    # 轻量 HTTP server（标准库 http.server，零依赖）
  tests/       # unittest 测试（零依赖）
frontend/      # React + TS + Vite（图导航 + 三视图）
```

## 技术栈

- **后端**：Python 标准库（`ast` / `tomllib` / `http.server`），零第三方依赖
- **前端**：React 18 + TypeScript + Vite；图布局用 `@dagrejs/dagre`
- **契约**：类型化 IR（`backend/ir/`），先校验后渲染，失败给规则码

## 运行测试

```bash
python -m unittest discover -s backend/tests -v
cd frontend && npm run build   # 含 tsc 类型检查
```
