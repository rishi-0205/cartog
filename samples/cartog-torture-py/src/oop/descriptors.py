# PATTERN: OOP-DESCRIPTOR-01 — descriptor
class D:
    def __get__(self, obj, typ): return 1
class C:
    x = D()
