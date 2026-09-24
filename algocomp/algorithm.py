"""The `Algorithm` record and the complexity-profile wrapper."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .complexity import Complexity, coerce


@dataclass(frozen=True)
class ComplexityProfile:
    """Best / average / worst-case complexities for one cost dimension.

    For time, `dimension` is "time"; for memory, "space". Extra named cases
    (e.g. "amortised") can be carried in `extra`.
    """

    worst: Complexity
    average: Complexity | None = None
    best: Complexity | None = None
    extra: dict[str, Complexity] = field(default_factory=dict)

    @property
    def headline(self) -> Complexity:
        """The complexity to quote when only one number is allowed."""
        return self.average or self.worst

    def items(self) -> list[tuple[str, Complexity]]:
        out: list[tuple[str, Complexity]] = []
        if self.best is not None:
            out.append(("best", self.best))
        if self.average is not None:
            out.append(("average", self.average))
        out.append(("worst", self.worst))
        out.extend(sorted(self.extra.items()))
        return out

    @property
    def is_case_sensitive(self) -> bool:
        """True when best/average/worst differ — i.e. input order matters."""
        vals = {c.expr for c in (self.best, self.average, self.worst) if c is not None}
        return len(vals) > 1


@dataclass(frozen=True)
class Algorithm:
    """A named algorithm with its theoretical cost profile.

    Attributes
    ----------
    name:
        Display name, e.g. ``"Merge Sort"``.
    key:
        Lookup key used on the CLI, e.g. ``"merge_sort"``.
    category:
        Family of algorithms, e.g. ``"sorting"``, ``"search"``, ``"graph"``.
    task:
        The problem it solves — two algorithms are comparable when they share a task.
    time / space:
        Complexity profiles.
    stable:
        Only meaningful for sorting: does it preserve equal-key order?
    in_place:
        Does it avoid O(n) auxiliary storage?
    notes:
        Free-form caveats (cache behaviour, constant factors, when to prefer it).
    """

    name: str
    key: str
    category: str
    task: str
    time: ComplexityProfile
    space: ComplexityProfile | None = None
    stable: bool | None = None
    in_place: bool | None = None
    notes: str = ""
    extra: dict[str, Any] = field(default_factory=dict)

    # ------------------------------------------------------------- factories

    @classmethod
    def build(
        cls,
        name: str,
        *,
        key: str | None = None,
        category: str = "custom",
        task: str = "custom",
        time_worst: str | Complexity,
        time_average: str | Complexity | None = None,
        time_best: str | Complexity | None = None,
        space_worst: str | Complexity = "1",
        space_average: str | Complexity | None = None,
        space_best: str | Complexity | None = None,
        stable: bool | None = None,
        in_place: bool | None = None,
        notes: str = "",
        **extra: Any,
    ) -> Algorithm:
        """Convenience constructor taking plain expression strings."""
        space = ComplexityProfile(
            worst=coerce(space_worst),
            average=coerce(space_average) if space_average is not None else None,
            best=coerce(space_best) if space_best is not None else None,
        )
        return cls(
            name=name,
            key=(key or _slugify(name)),
            category=category,
            task=task,
            time=ComplexityProfile(
                worst=coerce(time_worst),
                average=coerce(time_average) if time_average is not None else None,
                best=coerce(time_best) if time_best is not None else None,
            ),
            space=space,
            stable=stable,
            in_place=in_place,
            notes=notes,
            extra=extra,
        )

    # ------------------------------------------------------------------ misc

    @property
    def headline_time(self) -> Complexity:
        return self.time.headline

    @property
    def headline_space(self) -> Complexity | None:
        return self.space.headline if self.space else None

    def describe(self) -> str:
        bits = [f"{self.name} [{self.category}/{self.task}]"]
        bits.append(f"time  avg={self.time.average or '-'} worst={self.time.worst}")
        if self.space:
            bits.append(f"space avg={self.space.average or '-'} worst={self.space.worst}")
        if self.stable is not None:
            bits.append("stable" if self.stable else "unstable")
        return " | ".join(bits)


def _slugify(text: str) -> str:
    out = "".join(ch if ch.isalnum() else "_" for ch in text.lower())
    while "__" in out:
        out = out.replace("__", "_")
    return out.strip("_")


__all__ = ["Algorithm", "ComplexityProfile", "_slugify"]
