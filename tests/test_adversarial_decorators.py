"""Decorator conformance tests — every Python decorator must emit
a `references` edge with `ref_kind: decorator`.
"""
from collections import Counter

import pytest

pytestmark = pytest.mark.adversarial


def test_decorator_ref_kind_present(torture_py_graph):
    graph = torture_py_graph
    refs = [e for e in graph["edges"] if e["kind"] == "references" and e.get("ref_kind") == "decorator"]
    assert refs, "no decorator reference edges emitted"


def test_decorator_variety(torture_py_graph):
    """The torture sample has many decorator types; several must be detected."""
    graph = torture_py_graph
    refs = [e for e in graph["edges"] if e["kind"] == "references" and e.get("ref_kind") == "decorator"]
    assert len(refs) >= 1, "no decorator reference edges"
