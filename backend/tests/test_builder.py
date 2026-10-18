"""Builder 单元测试：静态扫描 → 骨架 IR。

运行：
    cd D:/代码可视化工具
    D:/python/python.exe -m unittest discover -s backend/tests -v
"""

import os
import tempfile
import unittest

from backend.builder.builder import build_ir, build_ir_from_files, load_or_build_ir
from backend.ir.validate import errors_only, validate

FIXTURES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "sample_project")


def _find_file(ir, suffix):
    for f in ir["files"]:
        if f["path"].endswith(suffix):
            return f
    return None


def _find_func(ir, file_suffix, name):
    f = _find_file(ir, file_suffix)
    if not f:
        return None
    for fn in f["functions"]:
        if fn["name"] == name:
            return fn
    return None


class TestBuilder(unittest.TestCase):
    def test_ir_valid(self):
        ir = build_ir(FIXTURES)
        self.assertEqual(errors_only(validate(ir)), [])

    def test_meta(self):
        ir = build_ir(FIXTURES)
        self.assertEqual(ir["schema_version"], 2)
        self.assertEqual(ir["meta"]["project"], "sample_project")
        self.assertEqual(ir["meta"]["generated_by"], "builder")

    def test_files_extracted(self):
        paths = {f["path"] for f in build_ir(FIXTURES)["files"]}
        self.assertIn("bad.py", paths)
        self.assertIn("good.py", paths)
        self.assertIn("importer.py", paths)
        self.assertIn("caller.py", paths)

    def test_functions_extracted(self):
        bad = _find_file(build_ir(FIXTURES), "bad.py")
        names = {fn["name"] for fn in bad["functions"]}
        self.assertIn("no_docstring", names)
        self.assertIn("bare_except", names)
        self.assertIn("one", names)  # 类方法也被抽取

    def test_signature_from_source_line(self):
        fn = _find_func(build_ir(FIXTURES), "bad.py", "clean")
        self.assertTrue(fn["signature"].startswith("def clean"))

    def test_import_dependency(self):
        ir = build_ir(FIXTURES)
        imp = _find_file(ir, "importer.py")
        good = _find_file(ir, "good.py")
        self.assertIn(
            {"from": imp["id"], "to": good["id"], "type": "import"}, ir["dependencies"]
        )

    def test_file_internal_call(self):
        ir = build_ir(FIXTURES)
        main = _find_func(ir, "caller.py", "main_flow")
        helper = _find_func(ir, "caller.py", "helper")
        self.assertIn(helper["id"], main["calls"])
        self.assertIn(main["id"], helper["called_by"])

    def test_rule_violations_mapped(self):
        ir = build_ir(FIXTURES)
        rules = {v["rule"] for v in ir["rule_violations"]}
        self.assertIn("R_BARE_EXCEPT", rules)
        self.assertIn("R_NO_DOCSTRING", rules)
        for v in ir["rule_violations"]:
            self.assertTrue(v["node"], "违规应映射到非空 node")

    def test_single_module_no_mod_deps(self):
        # fixtures 是平铺单目录 → 所有文件同属一个模块 → 无模块间依赖
        ir = build_ir(FIXTURES)
        self.assertEqual(len(ir["modules"]), 1)
        self.assertEqual(ir["module_dependencies"], [])


class TestLoadOrBuild(unittest.TestCase):
    def test_enriched_priority(self):
        ir, source = load_or_build_ir(FIXTURES)
        self.assertEqual(source, "enriched")
        self.assertEqual(ir["modules"][0]["layer"], "L2")
        self.assertTrue(ir["findings"])

    def test_skeleton_fallback(self):
        with tempfile.TemporaryDirectory() as tmp:
            with open(os.path.join(tmp, "a.py"), "w", encoding="utf-8") as fp:
                fp.write('def f():\n    """doc"""\n    return 1\n')
            ir, source = load_or_build_ir(tmp)
            self.assertEqual(source, "skeleton")
            self.assertEqual(ir["meta"]["generated_by"], "builder")

    def test_bad_enrich_falls_back(self):
        with tempfile.TemporaryDirectory() as tmp:
            with open(os.path.join(tmp, "a.py"), "w", encoding="utf-8") as fp:
                fp.write("def f():\n    return 1\n")
            with open(os.path.join(tmp, "enrich.ir.json"), "w", encoding="utf-8") as fp:
                fp.write("{invalid json")
            ir, source = load_or_build_ir(tmp)
            self.assertEqual(source, "skeleton")


class TestBuildFromFiles(unittest.TestCase):
    def test_build_from_memory_files(self):
        files = [
            {"path": "a.py", "content": 'def f():\n    """doc"""\n    return 1\n'},
            {"path": "pkg/b.py", "content": "def g():\n    return 2\n"},
        ]
        ir = build_ir_from_files(files, project_name="demo")
        self.assertEqual(errors_only(validate(ir)), [])
        self.assertEqual(ir["meta"]["project"], "demo")
        self.assertEqual(len(ir["files"]), 2)
        self.assertEqual(len(ir["modules"]), 2)

    def test_build_from_memory_with_violations(self):
        files = [
            {"path": "x.py", "content": "def f():\n    try:\n        pass\n    except:\n        pass\n"},
        ]
        ir = build_ir_from_files(files, "demo")
        rules = {v["rule"] for v in ir["rule_violations"]}
        self.assertIn("R_BARE_EXCEPT", rules)

    def test_build_from_memory_with_readme(self):
        files = [{"path": "a.py", "content": 'def f():\n    """doc"""\n    return 1\n'}]
        readme = "# My Project\n\n这是一个演示项目。\n\n## 安装\n\n```bash\npip install\n```\n"
        ir = build_ir_from_files(files, "demo", readme=readme)
        self.assertIn("overview", ir["meta"])
        self.assertIn("演示项目", ir["meta"]["overview"])
        self.assertNotIn("安装", ir["meta"]["overview"])  # 标题与代码块被剔除


if __name__ == "__main__":
    unittest.main(verbosity=2)
