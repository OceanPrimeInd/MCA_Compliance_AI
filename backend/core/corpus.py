"""Registry of ingested regulatory codes.

This is what a single-code competitor cannot answer against. Holding SPVC and
Workboat Code Edition 3 in one queryable layer makes three questions possible
that no per-code product can serve:

  - "Which code governs my vessel at all?"
  - "This 11m Category 2 vessel — what changes if it certificates under WBC3
     rather than SPVC?"
  - "I am moving from Edition 2 to Edition 3. What is new for me?"

A corpus whose index has not been built yet is registered but marked
unavailable, so the platform degrades to the codes it actually has rather than
failing at import.
"""

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from core.rag.retrieve import Retriever
from core.vessel import VesselProfile

DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "processed"


@dataclass(frozen=True)
class CorpusSpec:
    code_id: str
    code_name: str
    short_name: str
    index_filename: str
    description: str


REGISTERED_CORPORA = (
    CorpusSpec(
        code_id="spvc_2025",
        code_name="MCA Sport or Pleasure Vessel Code 2025",
        short_name="SPVC 2025",
        index_filename="spvc_2025_index.npz",
        description="Sport and pleasure vessels in commercial use.",
    ),
    CorpusSpec(
        code_id="wbc3",
        code_name="MCA Workboat Code Edition 3",
        short_name="Workboat Code Ed 3",
        index_filename="wbc3_index.npz",
        description="Small workboats and pilot boats. In force since 13 December 2023.",
    ),
)


class CorpusRegistry:
    """Loads every corpus whose index exists on disk."""

    def __init__(self, specs=REGISTERED_CORPORA, data_dir: Path = DATA_DIR):
        self.specs = {s.code_id: s for s in specs}
        self.retrievers: dict[str, Retriever] = {}
        self.unavailable: dict[str, str] = {}
        self.fingerprints: dict[str, str] = {}

        for spec in specs:
            index_path = data_dir / spec.index_filename
            if not index_path.exists():
                self.unavailable[spec.code_id] = (
                    f"index not built — run: python -m core.rag.build_index "
                    f"--chunks data/processed/{spec.code_id}_chunks.json"
                )
                print(f"[corpus] {spec.short_name}: unavailable ({index_path.name} missing)")
                continue

            self.retrievers[spec.code_id] = Retriever(str(index_path))
            self.fingerprints[spec.code_id] = self._fingerprint(index_path)
            print(
                f"[corpus] {spec.short_name}: loaded "
                f"(fingerprint {self.fingerprints[spec.code_id]})"
            )

        if not self.retrievers:
            raise RuntimeError(
                "No corpora available. Build at least one index before starting the API."
            )

    @staticmethod
    def _fingerprint(index_path: Path) -> str:
        """Short content hash of an index, recorded on every decision.

        Without this, a provenance record could not be trusted: re-ingesting a
        code would silently change what a past answer would have been, with
        nothing to show that the ground had moved. Hashing the file directly
        means any re-embed, re-chunk or corpus edit produces a different value.
        """
        digest = hashlib.sha256()
        with open(index_path, "rb") as handle:
            for block in iter(lambda: handle.read(1 << 20), b""):
                digest.update(block)
        return digest.hexdigest()[:12]

    @property
    def available_ids(self) -> list[str]:
        return list(self.retrievers.keys())

    def catalogue(self) -> list[dict]:
        return [
            {
                "code_id": s.code_id,
                "code_name": s.code_name,
                "short_name": s.short_name,
                "description": s.description,
                "available": s.code_id in self.retrievers,
                "reason": self.unavailable.get(s.code_id),
                "fingerprint": self.fingerprints.get(s.code_id),
            }
            for s in self.specs.values()
        ]

    def embed_query(self, question: str):
        """Any loaded retriever will do — they share one embedding model."""
        return next(iter(self.retrievers.values()))._embed_query(question)

    def search(
        self,
        question: str,
        top_k: int = 5,
        vessel: VesselProfile | None = None,
        code_ids: list[str] | None = None,
    ) -> dict:
        """Blended search across codes, ranked by score after filtering.

        Used for ordinary questions where the user does not care which document
        the answer came from, only that it binds their vessel.
        """
        targets = self._resolve(code_ids)

        merged, filtered = [], []
        for code_id in targets:
            spec = self.specs[code_id]
            # Over-fetch per code so the blend is chosen from a real pool
            # rather than being padded out by whichever code was asked first.
            outcome = self.retrievers[code_id].search(question, top_k=top_k, vessel=vessel)
            for r in outcome["results"]:
                r["code_id"] = code_id
                r["code_name"] = spec.code_name
                merged.append(r)
            for f in outcome["filtered_out"]:
                f["code_id"] = code_id
                f["code_name"] = spec.code_name
                filtered.append(f)

        merged.sort(key=lambda r: r["score"], reverse=True)
        return {
            "results": merged[:top_k],
            "filtered_out": filtered,
            "codes_searched": targets,
            "filtering_active": vessel is not None,
        }

    def compare(
        self,
        question: str,
        top_k: int = 4,
        vessel: VesselProfile | None = None,
        code_ids: list[str] | None = None,
    ) -> dict:
        """Per-code results, kept separate.

        Blending would destroy the comparison: the answer layer needs to see
        what each code says on its own before it can state what differs.
        """
        targets = self._resolve(code_ids)

        per_code, filtered = {}, []
        for code_id in targets:
            spec = self.specs[code_id]
            outcome = self.retrievers[code_id].search(question, top_k=top_k, vessel=vessel)
            for r in outcome["results"]:
                r["code_id"] = code_id
                r["code_name"] = spec.code_name
            per_code[code_id] = {
                "code_name": spec.code_name,
                "short_name": spec.short_name,
                "results": outcome["results"],
            }
            for f in outcome["filtered_out"]:
                f["code_id"] = code_id
                filtered.append(f)

        return {
            "per_code": per_code,
            "filtered_out": filtered,
            "codes_searched": targets,
            "filtering_active": vessel is not None,
        }

    def _resolve(self, code_ids: list[str] | None) -> list[str]:
        if not code_ids:
            return self.available_ids

        unknown = [c for c in code_ids if c not in self.specs]
        if unknown:
            raise ValueError(f"Unknown code_id(s): {', '.join(unknown)}")

        missing = [c for c in code_ids if c not in self.retrievers]
        if missing:
            reasons = "; ".join(f"{c}: {self.unavailable[c]}" for c in missing)
            raise ValueError(f"Corpus not available — {reasons}")

        return code_ids
