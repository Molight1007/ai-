"""enrich 语义填充的纯逻辑测试（不调 LLM）。"""

import unittest

from backend.enrich import _apply_patch, _parse_json, copy_unchanged


def _skeleton():
    return {
        "schema_version": 2,
        "meta": {"project": "p", "language": "python", "generated_by": "builder"},
        "modules": [{"id": "m1", "label": "模块一", "files": ["f1"]}],
        "files": [
            {"id": "f1", "path": "a.py", "module": "m1",
             "functions": [{"id": "g1", "name": "go"}]},
        ],
        "findings": [],
        "flows": [],
    }


class TestParseJson(unittest.TestCase):
    def test_plain(self):
        self.assertEqual(_parse_json('{"a": 1}'), {"a": 1})

    def test_fenced(self):
        reply = '好的：\n```json\n{"modules": []}\n```\n结束'
        self.assertEqual(_parse_json(reply), {"modules": []})


class TestApplyPatch(unittest.TestCase):
    def test_module_file_findings(self):
        ir = _skeleton()
        patch = {
            "modules": [{"id": "m1", "layer": "L2", "summary": "职责", "description": "详"}],
            "files": [{"id": "f1", "description": "文件详"}],
            "findings": [{"severity": "error", "node": "g1", "line": 1,
                          "title": "边界", "detail": "d", "suggestion": "s"}],
            "flows": [{"label": "主流程", "steps": ["g1", "g_missing"]}],
        }
        _apply_patch(ir, patch)
        self.assertEqual(ir["modules"][0]["layer"], "L2")
        self.assertEqual(ir["files"][0]["description"], "文件详")
        self.assertEqual(len(ir["findings"]), 1)
        self.assertEqual(ir["findings"][0]["severity"], "error")
        # 悬空 steps 被过滤后不足 2 步，flow 不加入
        self.assertEqual(ir["flows"], [])

    def test_invalid_layer_ignored(self):
        ir = _skeleton()
        _apply_patch(ir, {"modules": [{"id": "m1", "layer": "L9"}]})
        self.assertNotIn("layer", ir["modules"][0])

    def test_dangling_finding_node_ignored(self):
        ir = _skeleton()
        _apply_patch(ir, {"findings": [{"severity": "error", "node": "g_ghost", "title": "x"}]})
        self.assertEqual(ir["findings"], [])


class TestCopyUnchanged(unittest.TestCase):
    def test_preserve_unchanged_semantics(self):
        old_ir = {
            "schema_version": 2,
            "meta": {"project": "p", "language": "python", "generated_by": "builder"},
            "modules": [{"id": "m1", "label": "模块", "layer": "L2", "summary": "职责", "description": "详", "files": ["f1", "f2"]}],
            "files": [
                {"id": "f1", "path": "a.py", "module": "m1", "hash": "h1", "description": "文件1详",
                 "functions": [{"id": "g1", "name": "f", "summary": "s1", "description": "d1"}]},
                {"id": "f2", "path": "b.py", "module": "m1", "hash": "h2", "description": "文件2详",
                 "functions": [{"id": "g2", "name": "g", "summary": "s2", "description": "d2"}]},
            ],
        }
        new_ir = {
            "schema_version": 2,
            "meta": {"project": "p", "language": "python", "generated_by": "builder"},
            "modules": [{"id": "m1", "label": "模块", "files": ["f1", "f2"]}],
            "files": [
                {"id": "f1", "path": "a.py", "module": "m1", "hash": "h1",
                 "functions": [{"id": "g1", "name": "f"}]},
                {"id": "f2", "path": "b.py", "module": "m1", "hash": "h2_changed",
                 "functions": [{"id": "g2", "name": "g"}]},
            ],
        }
        unchanged = copy_unchanged(old_ir, new_ir)
        self.assertEqual(unchanged, {"f1"})
        # 未变文件 f1 语义保留
        self.assertEqual(new_ir["files"][0]["description"], "文件1详")
        self.assertEqual(new_ir["files"][0]["functions"][0]["summary"], "s1")
        # 变化文件 f2 语义不保留
        self.assertNotIn("description", new_ir["files"][1])
        # 模块含变化文件 → 模块语义不保留
        self.assertNotIn("layer", new_ir["modules"][0])

    def test_all_unchanged_preserves_module(self):
        old_ir = {
            "schema_version": 2,
            "meta": {"project": "p", "language": "python", "generated_by": "builder"},
            "modules": [{"id": "m1", "label": "模块", "layer": "L3", "summary": "s", "description": "d", "files": ["f1"]}],
            "files": [{"id": "f1", "path": "a.py", "module": "m1", "hash": "h1",
                       "functions": []}],
        }
        new_ir = {
            "schema_version": 2,
            "meta": {"project": "p", "language": "python", "generated_by": "builder"},
            "modules": [{"id": "m1", "label": "模块", "files": ["f1"]}],
            "files": [{"id": "f1", "path": "a.py", "module": "m1", "hash": "h1",
                       "functions": []}],
        }
        copy_unchanged(old_ir, new_ir)
        self.assertEqual(new_ir["modules"][0]["layer"], "L3")
        self.assertEqual(new_ir["modules"][0]["summary"], "s")


if __name__ == "__main__":
    unittest.main(verbosity=2)
