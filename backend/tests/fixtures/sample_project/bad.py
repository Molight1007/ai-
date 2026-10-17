"""测试用违规样例文件。"""


def clean():
    """有 docstring 的正常函数。"""
    return 1


def no_docstring():
    x = 1
    y = 2
    z = x + y
    return z


def too_long():
    a = 1
    b = 2
    c = 3
    d = 4
    e = 5
    f = 6
    g = 7
    return a + b + c + d + e + f + g


class FourMethods:
    """四方法类（用于低阈值触发上帝类）。"""

    def one(self):
        return 1

    def two(self):
        return 2

    def three(self):
        return 3

    def four(self):
        return 4


def bare_except():
    try:
        open("x")
    except:
        pass
