"""algo-compare — theoretical complexity comparison framework.

Compare two algorithms that solve the same task by their declared asymptotic
cost profiles (best / average / worst-case time *and* space), and get a
structured verdict: who wins asymptotically, by how much, from which input size
the advantage actually matters, and what the caveats are.

Quick start
-----------
    from algocomp import compare, registry

    reg = registry()
    v = compare(reg.get("merge_sort"), reg.get("quick_sort"))
    print(v.conclusion())
"""

from __future__ import annotations

__version__ = "1.0.0"

from .algorithm import Algorithm, ComplexityProfile
from .catalog import ALL_ALGORITHMS, CATEGORIES
from .comparator import CaseVerdict, Verdict, compare
from .complexity import HIERARCHY, Complexity, coerce
from .expr import ExprError, evaluate
from .registry import Registry, default_registry as registry, load_definitions, register_custom
from .reports import render, render_html, render_json, render_markdown, render_terminal

__all__ = [
    "__version__",
    "Algorithm",
    "ComplexityProfile",
    "Complexity",
    "HIERARCHY",
    "coerce",
    "evaluate",
    "ExprError",
    "compare",
    "Verdict",
    "CaseVerdict",
    "Registry",
    "registry",
    "load_definitions",
    "register_custom",
    "ALL_ALGORITHMS",
    "CATEGORIES",
    "render",
    "render_terminal",
    "render_markdown",
    "render_json",
    "render_html",
]
