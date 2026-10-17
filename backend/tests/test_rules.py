"""规则引擎单元测试（标准库 unittest，零依赖）。

运行：
    cd D:/代码可视化工具
    D:/python/python.exe -m unittest discover -s backend/tests -v
"""

import os
import unittest

from backend.rules.engine import analyze, load_rules

HERE = os.path.dirname(os.path.abspath(__file__))
FIXTURES = os.path.join(HERE, "fixtures", "sample_project")


def _custom_rules(**overrides):
    """构造一份自定义规则，便于低阈值触发（不真的写 150 行）。"""
    base = load_rules()
    for name, patch in overrides.items():
        base["rules"][name].update(patch)
    return base


def _violations(rules=None):
    return analyze(FIXTURES, rules if rules is not None else load_rules())


class TestLoadRules(unittest.TestCase):
    def test_load_default(self):
        rules = load_rules()
        self.assertIn("R_FUNC_LEN", rules["rules"])
        self.assertEqual(rules["rules"]["R_FUNC_LEN"]["max_lines"], 150)

    def test_all_rules_present(self):
        rules = load_rules()["rules"]
        for name in ("R_FUNC_LEN", "R_FILE_LEN", "R_GOD_CLASS", "R_NO_DOCSTRING", "R_BARE_EXCEPT"):
            self.assertIn(name, rules)


class TestDefaultRules(unittest.TestCase):
    def test_bare_except(self):
        self.assertTrue(any(v.rule == "R_BARE_EXCEPT" for v in _violations()))

    def test_no_docstring(self):
        vs = _violations()
        names = {v.name for v in vs if v.rule == "R_NO_DOCSTRING"}
        self.assertIn("no_docstring", names)

    def test_clean_func_not_flagged(self):
        vs = _violations()
        self.assertFalse(any(v.rule == "R_NO_DOCSTRING" and v.name == "clean" for v in vs))


class TestThresholds(unittest.TestCase):
    def test_func_len(self):
        vs = _violations(_custom_rules(R_FUNC_LEN={"max_lines": 5}))
        self.assertTrue(any(v.rule == "R_FUNC_LEN" and v.name == "too_long" for v in vs))

    def test_file_len(self):
        vs = _violations(_custom_rules(R_FILE_LEN={"max_lines": 20}))
        self.assertTrue(any(v.rule == "R_FILE_LEN" and v.path.endswith("bad.py") for v in vs))

    def test_god_class(self):
        vs = _violations(_custom_rules(R_GOD_CLASS={"max_methods": 3}))
        self.assertTrue(any(v.rule == "R_GOD_CLASS" and v.name == "FourMethods" for v in vs))


class TestGoodFile(unittest.TestCase):
    def test_good_file_no_violations(self):
        rules = _custom_rules(
            R_FUNC_LEN={"max_lines": 5}, R_GOD_CLASS={"max_methods": 3},
            R_FILE_LEN={"max_lines": 20},
        )
        vs = _violations(rules)
        self.assertFalse(any(v.path.endswith("good.py") for v in vs))


if __name__ == "__main__":
    unittest.main(verbosity=2)
