"""Vessel profile and statutory applicability model.

This is the context layer's state. A VesselProfile is captured once per vessel
and applied to every question, so a clause that cannot bind the vessel never
reaches the model.

Design rule that matters for a compliance product: filtering is CONSERVATIVE.
A clause is excluded only when its parsed scope explicitly and unambiguously
conflicts with the vessel. Anything unparsed, partial or ambiguous is kept.
Dropping a binding clause is a far worse failure than showing an extra one,
because the model can still say an extra clause does not apply — it cannot
recover a clause it was never given.
"""

from dataclasses import dataclass, field, asdict
from typing import Optional


VESSEL_TYPES = ("sport", "pleasure", "workboat", "commercial rib", "pilot boat")

# SPVC / WBC3 operating area categories. 0 is the least restricted (unlimited),
# 6 is the most restricted (smooth waters, close to shore).
AREA_CATEGORIES = tuple(range(0, 7))


@dataclass
class VesselProfile:
    """The verified attributes the context layer locks in for a user."""

    vessel_type: str
    length_overall: float           # metres
    area_category: int              # 0..6
    hull_material: str
    passenger_count: int

    def __post_init__(self):
        if self.area_category not in AREA_CATEGORIES:
            raise ValueError(f"area_category must be 0-6, got {self.area_category}")
        if self.length_overall <= 0:
            raise ValueError(f"length_overall must be positive, got {self.length_overall}")
        if self.passenger_count < 0:
            raise ValueError(f"passenger_count cannot be negative, got {self.passenger_count}")
        self.vessel_type = self.vessel_type.strip().lower()
        # Hull material keeps its given case: "GRP" is an acronym and
        # lower-casing it produces "Grp" everywhere it is displayed. Matching is
        # never done on this field, so normalising it buys nothing.
        self.hull_material = self.hull_material.strip()

    def describe(self) -> str:
        """One-line description injected into the prompt."""
        return (
            f"{self.length_overall}m {self.vessel_type} vessel, "
            f"{self.hull_material} hull, "
            f"operating area Category {self.area_category}, "
            f"carrying {self.passenger_count} passenger(s)"
        )

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Applicability:
    """The scope conditions parsed out of a single clause.

    Every field is optional. None means "the clause states no constraint on this
    axis", which is treated as "applies to all values of it".
    """

    length_min: Optional[float] = None      # metres, inclusive lower bound
    length_max: Optional[float] = None      # metres, exclusive upper bound
    categories: Optional[frozenset] = None  # set of ints the clause is scoped to
    passengers_min: Optional[int] = None
    passengers_max: Optional[int] = None
    vessel_types: Optional[frozenset] = None
    evidence: tuple = field(default_factory=tuple)  # phrases matched, for audit

    def is_unconstrained(self) -> bool:
        return not any(
            v is not None
            for v in (
                self.length_min,
                self.length_max,
                self.categories,
                self.passengers_min,
                self.passengers_max,
                self.vessel_types,
            )
        )

    def conflicts_with(self, vessel: VesselProfile) -> Optional[str]:
        """Return a reason string if this clause CANNOT bind the vessel, else None.

        Only explicit, parsed conflicts are reported. Silence means "keep it".
        """
        loa = vessel.length_overall

        if self.length_min is not None and loa < self.length_min:
            return f"clause scoped to vessels of {self.length_min}m and over; vessel is {loa}m"

        if self.length_max is not None and loa >= self.length_max:
            return f"clause scoped to vessels under {self.length_max}m; vessel is {loa}m"

        if self.categories is not None and vessel.area_category not in self.categories:
            listed = ", ".join(str(c) for c in sorted(self.categories))
            return f"clause scoped to Category {listed}; vessel is Category {vessel.area_category}"

        if self.passengers_min is not None and vessel.passenger_count < self.passengers_min:
            return (
                f"clause scoped to vessels carrying more than {self.passengers_min - 1} passengers; "
                f"vessel carries {vessel.passenger_count}"
            )

        if self.passengers_max is not None and vessel.passenger_count > self.passengers_max:
            return (
                f"clause scoped to vessels carrying up to {self.passengers_max} passengers; "
                f"vessel carries {vessel.passenger_count}"
            )

        if self.vessel_types is not None and vessel.vessel_type not in self.vessel_types:
            listed = ", ".join(sorted(self.vessel_types))
            return f"clause scoped to {listed} vessels; vessel is a {vessel.vessel_type}"

        return None

    def describe_scope(self) -> str:
        """Human-readable scope condition for the Statutory Reference Matrix."""
        parts = []

        if self.length_min is not None and self.length_max is not None:
            parts.append(f"vessels {self.length_min}m to under {self.length_max}m")
        elif self.length_min is not None:
            parts.append(f"vessels {self.length_min}m and over")
        elif self.length_max is not None:
            parts.append(f"vessels under {self.length_max}m")

        if self.categories is not None:
            listed = ", ".join(str(c) for c in sorted(self.categories))
            parts.append(f"operating in Category {listed}")

        if self.passengers_min is not None:
            parts.append(f"carrying {self.passengers_min} or more passengers")
        if self.passengers_max is not None:
            parts.append(f"carrying up to {self.passengers_max} passengers")

        if self.vessel_types is not None:
            parts.append(", ".join(sorted(self.vessel_types)) + " vessels")

        return "; ".join(parts) if parts else "all vessels within the scope of the Code"

    def to_dict(self) -> dict:
        return {
            "length_min": self.length_min,
            "length_max": self.length_max,
            "categories": sorted(self.categories) if self.categories is not None else None,
            "passengers_min": self.passengers_min,
            "passengers_max": self.passengers_max,
            "vessel_types": sorted(self.vessel_types) if self.vessel_types is not None else None,
            "evidence": list(self.evidence),
        }

    @classmethod
    def from_dict(cls, d: Optional[dict]) -> "Applicability":
        if not d:
            return cls()
        return cls(
            length_min=d.get("length_min"),
            length_max=d.get("length_max"),
            categories=frozenset(d["categories"]) if d.get("categories") is not None else None,
            passengers_min=d.get("passengers_min"),
            passengers_max=d.get("passengers_max"),
            vessel_types=frozenset(d["vessel_types"]) if d.get("vessel_types") is not None else None,
            evidence=tuple(d.get("evidence", [])),
        )
