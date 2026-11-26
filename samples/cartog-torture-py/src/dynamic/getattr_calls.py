# PATTERN: DYN-GETATTR-01 — getattr(obj,name)() (abstain)
class C:
    def m(self): pass
getattr(C(), "m")()
