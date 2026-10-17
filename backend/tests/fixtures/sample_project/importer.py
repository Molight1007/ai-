"""导入示例文件：用于验证文件级 import 依赖抽取。"""

from good import add


def use_add(a, b):
    """调用 good.add。"""
    return add(a, b)
