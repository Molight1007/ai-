"""IR 校验器单元测试（标准库 unittest，零依赖）。

运行：
    cd D:/代码可视化工具
    D:/python/python.exe -m unittest discover -s backend/tests -v
"""

import json
import os
import unittest

from backend.ir.validate import validate, errors_only

HERE = os.path.dirname(os.path.abspath(__file__))
EXAMPLES = os.path.join(HERE, "..", "examples")


def _valid():
    """返回一份最小合法 IR（作为基准，逐项改坏来测规则码）。"""
    return {
        "schema_version": 2,
        "meta": {"project": "p", "language": "python", "generated_by": "x"},
        "modules": [
            {"id": "m1", "label": "模块一", "files": ["f1"]},
            {"id": "m2", "label": "模块二", "files": []},
        ],
        "files": [
            {"id": "f1", "path": "a.py", "module": "m1",
             "functions": [{"id": "g1", "name": "go", "line": 1, "end_line": 5,
                            "calls": [], "called_by": []}]},
        ],
    }


def _codes(ir):
    return {i.code for i in validate(ir)}


class TestValid(unittest.TestCase):
    def test_min_valid_passes(self):
        self.assertEqual(validate(_valid()), [])

    def test_sample_valid_file_passes(self):
        with open(os.path.join(EXAMPLES, "sample_valid.ir.json"), encoding="utf-8") as fp:
            ir = json.load(fp)
        self.assertEqual(errors_only(validate(ir)), [])


class TestStructural(unittest.TestCase):
    def test_bad_version(self):
        ir = _valid(); ir["schema_version"] = 1
        self.assertIn("IR/BAD_VERSION", _codes(ir))

    def test_missing_top_key(self):
        ir = _valid(); del ir["meta"]
        self.assertIn("IR/MISSING_KEY", _codes(ir))

    def test_missing_meta_field(self):
        ir = _valid(); del ir["meta"]["generated_by"]
        self.assertIn("IR/MISSING_KEY", _codes(ir))

    def test_bad_root_type(self):
        self.assertIn("IR/BAD_TYPE", _codes([]))

    def test_duplicate_id(self):
        ir = _valid()
        ir["modules"][1]["id"] = "m1"
        self.assertIn("IR/DUPLICATE_ID", _codes(ir))

    def test_bad_id_format(self):
        ir = _valid()
        ir["modules"][0]["id"] = "1bad"
        self.assertIn("IR/BAD_ID", _codes(ir))

    def test_empty_files(self):
        ir = _valid(); ir["files"] = []
        self.assertIn("IR/EMPTY_COLLECTION", _codes(ir))

    def test_empty_modules(self):
        ir = _valid(); ir["modules"] = []
        self.assertIn("IR/EMPTY_COLLECTION", _codes(ir))

    def test_bad_layer(self):
        ir = _valid(); ir["modules"][0]["layer"] = "L9"
        self.assertIn("IR/BAD_LAYER", _codes(ir))


class TestReferences(unittest.TestCase):
    def test_dangling_module(self):
        ir = _valid(); ir["files"][0]["module"] = "m_ghost"
        self.assertIn("IR/DANGLING_MODULE", _codes(ir))

    def test_dangling_file_in_module(self):
        ir = _valid(); ir["modules"][0]["files"] = ["f_ghost"]
        self.assertIn("IR/DANGLING_FILE", _codes(ir))

    def test_dangling_dep_ref(self):
        ir = _valid()
        ir["dependencies"] = [{"from": "f1", "to": "f_never"}]
        self.assertIn("IR/DANGLING_REF", _codes(ir))

    def test_dangling_flow_step(self):
        ir = _valid()
        ir["flows"] = [{"id": "fl", "label": "主流程", "steps": ["g1", "g_missing"]}]
        self.assertIn("IR/DANGLING_NODE", _codes(ir))

    def test_dangling_finding_node(self):
        ir = _valid()
        ir["findings"] = [{"id": "F", "severity": "error", "node": "g_ghost", "title": "x"}]
        self.assertIn("IR/DANGLING_NODE", _codes(ir))

    def test_dangling_module_dep(self):
        ir = _valid()
        ir["module_dependencies"] = [{"from": "m1", "to": "m_ghost"}]
        self.assertIn("IR/DANGLING_REF", _codes(ir))


class TestFieldValues(unittest.TestCase):
    def test_bad_severity(self):
        ir = _valid()
        ir["findings"] = [{"id": "F", "severity": "fatal", "node": "g1", "title": "x"}]
        self.assertIn("IR/BAD_SEVERITY", _codes(ir))

    def test_bad_line_negative(self):
        ir = _valid(); ir["files"][0]["lines"] = -1
        self.assertIn("IR/BAD_LINE", _codes(ir))

    def test_end_line_before_line(self):
        ir = _valid()
        ir["files"][0]["functions"][0]["line"] = 300
        ir["files"][0]["functions"][0]["end_line"] = 120
        self.assertIn("IR/BAD_LINE", _codes(ir))


if __name__ == "__main__":
    unittest.main(verbosity=2)
