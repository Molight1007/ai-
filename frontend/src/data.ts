// P2/P3 阶段的 mock 数据：内联 IR + 文件内容映射。
// P7 接入 FastAPI 后，这里替换为 fetch('/api/ir') 与 fetch(`/api/file?path=…`)。

import type { IR } from './types'

export const SAMPLE_IR: IR = {
  schema_version: 2,
  meta: {
    project: 'math-ai-evaluator',
    language: 'python',
    generated_by: 'workbuddy',
    generated_at: '2026-10-17T21:00:00Z',
    rules_version: '1.0',
    stats: { files: 4, lines: 4558, functions: 4, errors: 1, warnings: 1 },
  },
  modules: [
    {
      id: 'm_agent', label: 'agent 编排层', layer: 'L4',
      summary: '流程调度、阶段串联、异常处理',
      description:
        '负责把解题流程（规划 → 求解 → 验证）按序串起来，维护全局运行状态，并记录各阶段开始/结束用于统计与计时。本身不执行具体求解计算。',
      files: ['f_orchestrator', 'f_base'],
    },
    {
      id: 'm_biz', label: '业务求解', layer: 'L2',
      summary: '具体求解逻辑',
      description:
        '包含逐步推理、子目标分解等核心业务，是解题质量的直接决定层。依赖契约层的数据结构、调用工具层的能力。',
      files: ['f_solver'],
    },
    {
      id: 'm_tool', label: '工具层', layer: 'L1',
      summary: '通用 IO 能力',
      description:
        '提供文件读写等与业务无关的基础能力，被上层复用。只依赖契约层，不得反向依赖业务层。',
      files: ['f_util'],
    },
  ],
  files: [
    {
      id: 'f_orchestrator', path: 'agent/orchestrator.py', module: 'm_agent',
      language: 'python', lines: 3728,
      summary: '研究期主流程编排',
      description:
        '主流程编排器：按 steps 顺序调度各阶段，维护全局状态 RunState，是系统的入口调度中枢。',
      functions: [
        {
          id: 'fn_run', name: 'run_pipeline', line: 118, end_line: 126,
          signature: 'def run_pipeline(self, ctx: TaskContext) -> RunState',
          summary: '串起主流程',
          description:
            '遍历 steps，按 plan / solve / verify 分派到对应阶段方法，最后返回 RunState。是整个求解流程的唯一入口。',
          calls: ['fn_solve'], called_by: [],
        },
      ],
    },
    {
      id: 'f_base', path: 'agent/base.py', module: 'm_agent',
      language: 'python', lines: 210,
      summary: '数据结构契约',
      description:
        '定义全项目共享的数据结构（任务上下文、运行状态），不含业务逻辑，是各层之间的数据契约。',
      functions: [
        {
          id: 'fn_context', name: 'TaskContext', line: 10, end_line: 60,
          signature: 'class TaskContext',
          summary: '任务上下文',
          description: '承载题目与配置，贯穿整个求解过程。',
          calls: [], called_by: [],
        },
      ],
    },
    {
      id: 'f_solver', path: 'agent/solver.py', module: 'm_biz',
      language: 'python', lines: 540,
      summary: '逐步求解',
      description:
        '逐步求解器：对每个子目标做单步推理，把中间步骤写入 RunState.log，供下游验证阶段使用。',
      functions: [
        {
          id: 'fn_solve', name: 'solve_step', line: 88, end_line: 100,
          signature: 'def solve_step(self, state: RunState) -> None',
          summary: '单步推理',
          description:
            '处理一个求解步骤并更新状态日志。当前实现存在边界问题（空列表未处理），见审查清单。',
          calls: ['fn_read'], called_by: ['fn_run'],
        },
      ],
    },
    {
      id: 'f_util', path: 'utils/io.py', module: 'm_tool',
      language: 'python', lines: 80,
      summary: '文件读写',
      description: '通用文件读写工具，提供 JSON 读取等能力，供业务层调用。',
      functions: [
        {
          id: 'fn_read', name: 'read_json', line: 5, end_line: 30,
          signature: 'def read_json(path: str) -> dict',
          summary: '读 JSON',
          description: '读取指定路径的 JSON 文件并返回 dict，供求解器加载配置。',
          calls: [], called_by: ['fn_solve'],
        },
      ],
    },
  ],
  dependencies: [
    { from: 'f_orchestrator', to: 'f_solver', type: 'import' },
    { from: 'f_orchestrator', to: 'f_base', type: 'import' },
    { from: 'f_solver', to: 'f_util', type: 'call' },
  ],
  module_dependencies: [
    { from: 'm_agent', to: 'm_biz', type: 'import' },
    { from: 'm_biz', to: 'm_tool', type: 'call' },
  ],
  flows: [
    { id: 'flow_main', label: '解题主流程', steps: ['fn_run', 'fn_solve'] },
  ],
  rule_violations: [
    { id: 'V1', rule: 'R_FUNC_LEN', node: 'fn_run', line: 118,
      detail: '函数 180 行，超 150 行硬线', suggestion: '拆成子函数', severity: 'warning' },
    { id: 'V2', rule: 'R_NO_DOCSTRING', node: 'fn_solve', line: 88,
      detail: '函数 solve_step 缺 docstring', suggestion: '补一句职责说明', severity: 'info' },
  ],
  findings: [
    { id: 'F1', severity: 'error', type: 'logic_bug', node: 'fn_solve', line: 88,
      title: '边界条件遗漏', detail: '空列表未处理会抛 IndexError', suggestion: '加 len==0 分支' },
  ],
}

// 文件内容映射（P2 mock；P7 起由后端 /api/file 现读）
export const FILE_CONTENTS: Record<string, string> = {
  'agent/orchestrator.py': `"""研究期主流程编排。"""

class Orchestrator:
    def __init__(self, steps):
        self.steps = steps

    def run_pipeline(self, ctx: TaskContext) -> RunState:
        """串起主流程。"""
        state = RunState()
        for step in self.steps:
            if step == "plan":
                self._plan(ctx, state)
            elif step == "solve":
                self._solve(ctx, state)
        return state
`,
  'agent/base.py': `"""数据结构契约。"""

class TaskContext:
    def __init__(self, problem: str, config: dict):
        self.problem = problem
        self.config = config

class RunState:
    def __init__(self):
        self.result = None
        self.log = []
`,
  'agent/solver.py': `"""逐步求解。"""

class Solver:
    def solve_step(self, state: RunState) -> None:
        """单步推理。"""
        steps = state.log
        for s in steps:
            if not s:
                continue
        return None
`,
  'utils/io.py': `"""文件读写。"""

import json

def read_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as fp:
        return json.load(fp)
`,
}
