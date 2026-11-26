# PATTERN: DYN-METACLASS-01 — metaclass dispatch
class Meta(type):
    def __call__(cls, *a): return super().__call__(*a)
class C(metaclass=Meta): pass
C()
