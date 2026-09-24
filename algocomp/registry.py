"""Registry: catalogue lookup, fuzzy search and custom-algorithm loading."""

from __future__ import annotations

import difflib
import os
import re
from typing import Iterable

from .algorithm import Algorithm
from .catalog import ALL_ALGORITHMS, CATEGORIES
from .complexity import coerce


class Registry:
    """Holds every known algorithm, indexed by key, name and alias."""

    def __init__(self, algorithms: Iterable[Algorithm] = ALL_ALGORITHMS) -> None:
        self._by_key: dict[str, Algorithm] = {}
        self._aliases: dict[str, str] = {}
        self._categories: dict[str, str] = {}
        self.order: list[str] = []
        for algo in algorithms:
            self.add(algo)

    # ------------------------------------------------------------------ add

    def add(self, algo: Algorithm, *, replace: bool = True) -> None:
        key = _slug(algo.key)
        if key in self._by_key and not replace:
            raise KeyError(f"algorithm {key!r} already registered")
        if key not in self._by_key:
            self.order.append(key)
        self._by_key[key] = algo
        self._register_alias(algo.name, key)
        self._register_alias(key, key)
        for word in re.split(r"[^a-z0-9]+", algo.name.lower()):
            if len(word) > 2:
                self._aliases.setdefault(word, key)
        # keep the human-readable category for filter hints
        self._categories.setdefault(_slug(algo.category), algo.category)

    def _register_alias(self, alias: str, key: str) -> None:
        a = _slug(alias)
        self._aliases[a] = key
        self._aliases[a.replace("_", "")] = key
        self._aliases[a.replace("_", "-")] = key

    # --------------------------------------------------------------- lookup

    def __len__(self) -> int:
        return len(self._by_key)

    def __iter__(self):
        return (self._by_key[k] for k in self.order)

    def keys(self) -> list[str]:
        return list(self.order)

    def all(self) -> list[Algorithm]:
        return [self._by_key[k] for k in self.order]

    def get(self, query: str) -> Algorithm:
        """Exact, alias, or fuzzy lookup. Raises `LookupError` with suggestions."""
        slug = _slug(query)
        if slug in self._by_key:
            return self._by_key[slug]
        if slug in self._aliases:
            return self._by_key[self._aliases[slug]]
        flat = slug.replace("_", "")
        if flat in self._aliases:
            return self._by_key[self._aliases[flat]]

        candidates = list(self._aliases) + self.order
        matches = difflib.get_close_matches(slug, candidates, n=5, cutoff=0.55)
        # prefer matches on the human-readable name
        name_matches = [
            a.name for a in self.all()
            if difflib.SequenceMatcher(None, slug.replace("_", " "), a.name.lower()).ratio() > 0.6
        ]
        suggestions = list(dict.fromkeys(
            [self._aliases.get(m, m) for m in matches] + [a.key for a in self.all() if a.name in name_matches]
        ))[:5]
        hint = f" Did you mean: {', '.join(suggestions)}?" if suggestions else ""
        raise LookupError(f"unknown algorithm {query!r}.{hint}")

    # ------------------------------------------------------------- filtering

    def filter(
        self,
        *,
        category: str | None = None,
        task: str | None = None,
        query: str | None = None,
    ) -> list[Algorithm]:
        out = self.all()
        if category:
            c = _slug(category)
            out = [a for a in out if _slug(a.category).startswith(c) or c in _slug(a.category)]
        if task:
            t = _slug(task)
            out = [a for a in out if t in _slug(a.task)]
        if query:
            q = _slug(query)
            out = [a for a in out if q in _slug(a.name) or q in _slug(a.key)
                   or q in _slug(a.task) or q in _slug(a.category)]
        return out

    def categories(self) -> list[str]:
        """Category display names, catalogue order first."""
        return list(CATEGORIES) + sorted(
            {a.category for a in self.all()} - set(CATEGORIES)
        )

    def category_name(self, slug: str) -> str:
        """Map a slugified category back to its display name."""
        return self._categories.get(_slug(slug), slug)

    def comparable_with(self, algo: Algorithm) -> list[Algorithm]:
        """Algorithms solving the same task (the fair comparison set).

        Matching is by task *family*, so entries that differ only in their
        preconditions (e.g. "…non-negative weights" vs "…possibly negative
        weights") are still grouped and flagged for comparison.
        """
        family = task_family(algo.task)
        return [a for a in self.all() if a.key != algo.key and task_family(a.task) == family]

    def same_category(self, algo: Algorithm) -> list[Algorithm]:
        return [a for a in self.all() if a.key != algo.key and a.category == algo.category]


def task_family(task: str) -> str:
    """Normalise a task description so qualifiers don't split a family.

    "single-source shortest path, non-negative weights" and "single-source
    shortest path, possibly negative weights" belong to the same family
    ("single source shortest path"), which is what makes them comparable.
    """
    text = str(task).strip().lower()
    for sep in (",", " with ", " using ", " — ", " - ", " ("):
        text = text.split(sep)[0]
    return _slug(text)


def _slug(text: str) -> str:
    out = "".join(ch if ch.isalnum() else "_" for ch in str(text).lower())
    return re.sub(r"_+", "_", out).strip("_")


# --------------------------------------------------------------------------- #
# Custom algorithm definition files
# --------------------------------------------------------------------------- #

_COMMENT = re.compile(r"(^|\s)[#;].*$")


def load_definitions(path: str | os.PathLike[str], registry: Registry | None = None) -> list[Algorithm]:
    """Load extra algorithms from a simple INI-style file.

    Example::

        [my_sort]
        name = My Hybrid Sort
        category = sorting
        task = sort a list of comparable items
        time_worst = n*log2(n)
        time_average = n*log2(n)
        time_best = n
        space_worst = log2(n)
        stable = true
        in_place = true
        notes = Insertion sort below 32 elements, merge sort above.

    Recognised keys: name, category, task, time_worst/average/best,
    space_worst/average/best, stable, in_place, notes. Anything else is stored
    as free-form metadata.
    """
    registry = registry or default_registry()
    text = os.fspath(path)
    with open(text, "r", encoding="utf-8") as fh:
        raw = fh.read()

    loaded: list[Algorithm] = []
    section: str | None = None
    fields: dict[str, str] = {}

    def flush() -> None:
        if section is None:
            return
        loaded.append(_algo_from_fields(section, fields, registry))

    for line in raw.splitlines():
        line = _COMMENT.sub("", line).strip()
        if not line:
            continue
        m = re.fullmatch(r"\[([^\]]+)\]", line)
        if m:
            flush()
            section = m.group(1).strip()
            fields = {}
            continue
        if section is None:
            continue
        if "=" in line:
            key, _, value = line.partition("=")
            fields[key.strip().lower()] = value.strip()
        elif ":" in line:
            key, _, value = line.partition(":")
            fields[key.strip().lower()] = value.strip()
    flush()
    return loaded


_BOOLS = {"true": True, "yes": True, "1": True, "false": False, "no": False, "0": False,
          "": None, "none": None, "null": None, "-": None, "?": None, "unknown": None}


def _algo_from_fields(key: str, fields: dict[str, str], registry: Registry) -> Algorithm:
    if not fields.get("time_worst") and not fields.get("time"):
        raise ValueError(f"[{key}] needs at least 'time_worst' (or 'time')")

    def opt(name: str) -> str | None:
        v = fields.get(name)
        return v or None

    def boolean(name: str) -> bool | None:
        v = fields.get(name)
        if v is None:
            return None
        norm = v.strip().lower()
        if norm in _BOOLS:
            return _BOOLS[norm]
        raise ValueError(f"[{key}] {name}={v!r} is not a boolean")

    known = {"name", "category", "task", "time", "time_worst", "time_average", "time_best",
             "space", "space_worst", "space_average", "space_best", "stable", "in_place", "notes"}
    extra = {k: v for k, v in fields.items() if k not in known}

    return Algorithm.build(
        fields.get("name", key.replace("_", " ").title()),
        key=key,
        category=fields.get("category", "custom"),
        task=fields.get("task", "custom"),
        time_worst=opt("time_worst") or fields["time"],
        time_average=opt("time_average"),
        time_best=opt("time_best"),
        space_worst=opt("space_worst") or opt("space") or "1",
        space_average=opt("space_average"),
        space_best=opt("space_best"),
        stable=boolean("stable"),
        in_place=boolean("in_place"),
        notes=fields.get("notes", ""),
        **extra,
    )


_REGISTRY: Registry | None = None


def default_registry() -> Registry:
    """Process-wide registry seeded with the built-in catalogue."""
    global _REGISTRY
    if _REGISTRY is None:
        _REGISTRY = Registry()
    return _REGISTRY


def register_custom(
    name: str,
    *,
    time_worst: str,
    time_average: str | None = None,
    time_best: str | None = None,
    space_worst: str = "1",
    category: str = "custom",
    task: str = "custom",
    notes: str = "",
    registry: Registry | None = None,
    **extra: str,
) -> Algorithm:
    """Build + register one algorithm on the fly (used by `compare --add`)."""
    reg = registry or default_registry()
    algo = Algorithm.build(
        name,
        category=category,
        task=task,
        time_worst=coerce(time_worst).expr,
        time_average=coerce(time_average).expr if time_average else None,
        time_best=coerce(time_best).expr if time_best else None,
        space_worst=coerce(space_worst).expr,
        notes=notes,
        **extra,
    )
    reg.add(algo)
    return algo


def load_definitions_into(path, registry: Registry) -> list[Algorithm]:
    """`load_definitions` + register every algorithm it returns."""
    loaded = load_definitions(path, registry)
    for algo in loaded:
        registry.add(algo)
    return loaded


__all__ = ["Registry", "default_registry", "load_definitions", "load_definitions_into",
           "register_custom", "task_family", "_slug"]
