"""Sanctuary Typology Blueprint & Chronological Plan of Salvation Engine (WP-032).

Provides deterministic access to the Hebrew sanctuary architecture, furniture articles,
daily and yearly sacrificial services, Christological fulfillment, and the chronological
plan of salvation roadmap per Fundamental Belief #24 and ADR-025.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
import re
import threading
from typing import Any, Optional

from search.corpus.bible_books import parse_passage_ref
from search.resource import data_path

VALID_COMPARTMENTS = frozenset({"courtyard", "holy_place", "most_holy_place"})
_STRONGS_RE = re.compile(r"^[HG]\d{1,5}$")


def _normalize_range(v_start: Optional[int], v_end: Optional[int]) -> tuple[int, int]:
    """Normalize verse range boundaries for overlap calculations."""
    if v_start is None:
        return (1, 999)
    return (v_start, v_start if v_end is None else v_end)


@dataclass(frozen=True)
class SanctuaryCompartment:
    """A spatial compartment in the Sanctuary."""
    id: str
    name: str
    hebrew_name: str
    transliteration: str
    significance: str
    dimensions: str
    materials: str
    stations: list[str]
    spiritual_reality: str
    scriptures: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SanctuaryStation:
    """An article of furniture or sacred station in the Sanctuary."""
    id: str
    name: str
    common_name: str
    compartment: str
    hebrew_name: str
    transliteration: str
    strongs: list[str]
    materials: str
    position: str
    theological_meaning: str
    spiritual_reality: str
    ot_passages: list[str]
    nt_fulfillment: list[str]
    priestly_service: str
    sda_consensus: str
    svg_coords: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AnnotatedSanctuaryStation:
    """A sanctuary station annotated with contextual match metadata for a passage or verse."""
    id: str
    name: str
    common_name: str
    compartment: str
    compartment_name: str
    hebrew_name: str
    transliteration: str
    strongs: list[str]
    materials: str
    position: str
    theological_meaning: str
    spiritual_reality: str
    ot_passages: list[str]
    nt_fulfillment: list[str]
    priestly_service: str
    sda_consensus: str
    svg_coords: dict[str, Any]
    is_ot_institution: bool = False
    is_nt_fulfillment: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_station(
        cls,
        station: SanctuaryStation,
        compartment_name: str,
        is_ot: bool = False,
        is_nt: bool = False,
    ) -> AnnotatedSanctuaryStation:
        return cls(
            id=station.id,
            name=station.name,
            common_name=station.common_name,
            compartment=station.compartment,
            compartment_name=compartment_name,
            hebrew_name=station.hebrew_name,
            transliteration=station.transliteration,
            strongs=list(station.strongs),
            materials=station.materials,
            position=station.position,
            theological_meaning=station.theological_meaning,
            spiritual_reality=station.spiritual_reality,
            ot_passages=list(station.ot_passages),
            nt_fulfillment=list(station.nt_fulfillment),
            priestly_service=station.priestly_service,
            sda_consensus=station.sda_consensus,
            svg_coords=dict(station.svg_coords),
            is_ot_institution=is_ot,
            is_nt_fulfillment=is_nt,
        )


@dataclass(frozen=True)
class SanctuaryService:
    """A sacrificial priestly service in the Hebrew sanctuary system."""
    id: str
    name: str
    hebrew_name: str
    transliteration: str
    frequency: str
    location: str
    participants: str
    focus: str
    process: str
    christological_antitype: str
    scriptures: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PlanOfSalvationPhase:
    """A chronological progression phase in the Plan of Salvation."""
    id: str
    stage_number: int
    title: str
    symbolic_compartment: str
    symbolic_furniture: list[str]
    prophetic_time: str
    historical_event: str
    theological_significance: str
    biblical_anchors: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class SanctuaryEngine:
    """Deterministic, thread-safe query engine for the Sanctuary Typological Blueprint."""

    def __init__(self, schema_path: Optional[Path] = None) -> None:
        path = schema_path or data_path("sanctuary_schema.json")
        if not path.is_file():
            raise FileNotFoundError(f"Sanctuary schema dataset not found at {path}")

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self._raw = data
        self._version = data.get("version", "1.0.0")
        self._title = data.get("title", "")
        self._description = data.get("description", "")

        # Compartments
        self._compartments: list[SanctuaryCompartment] = []
        self._compartment_by_id: dict[str, SanctuaryCompartment] = {}
        for c in data.get("compartments", []):
            comp_id = c["id"]
            if comp_id not in VALID_COMPARTMENTS:
                raise ValueError(f"Unrecognized compartment id {comp_id!r}")
            comp = SanctuaryCompartment(
                id=comp_id,
                name=c["name"],
                hebrew_name=c.get("hebrew_name", ""),
                transliteration=c.get("transliteration", ""),
                significance=c.get("significance", ""),
                dimensions=c.get("dimensions", ""),
                materials=c.get("materials", ""),
                stations=list(c.get("stations", [])),
                spiritual_reality=c.get("spiritual_reality", ""),
                scriptures=list(c.get("scriptures", [])),
            )
            self._compartments.append(comp)
            self._compartment_by_id[comp_id] = comp

        # Stations
        self._stations: list[SanctuaryStation] = []
        self._station_by_id: dict[str, SanctuaryStation] = {}
        self._station_compartment_names: dict[str, str] = {}
        self._ot_ranges: dict[str, list[tuple[str, int, int, int]]] = {}
        self._nt_ranges: dict[str, list[tuple[str, int, int, int]]] = {}

        for s in data.get("stations", []):
            st_id = s["id"]
            comp_id = s["compartment"]
            if comp_id not in VALID_COMPARTMENTS:
                raise ValueError(f"Station {st_id!r} has invalid compartment {comp_id!r}")

            strongs_codes = [c.upper().strip() for c in s.get("strongs", [])]
            for sc in strongs_codes:
                if not _STRONGS_RE.match(sc):
                    raise ValueError(f"Invalid Strong's code {sc!r} in sanctuary station {st_id!r}")

            station = SanctuaryStation(
                id=st_id,
                name=s["name"],
                common_name=s.get("common_name", s["name"]),
                compartment=comp_id,
                hebrew_name=s.get("hebrew_name", ""),
                transliteration=s.get("transliteration", ""),
                strongs=strongs_codes,
                materials=s.get("materials", ""),
                position=s.get("position", ""),
                theological_meaning=s.get("theological_meaning", ""),
                spiritual_reality=s.get("spiritual_reality", ""),
                ot_passages=list(s.get("ot_passages", [])),
                nt_fulfillment=list(s.get("nt_fulfillment", [])),
                priestly_service=s.get("priestly_service", ""),
                sda_consensus=s.get("sda_consensus", ""),
                svg_coords=dict(s.get("svg_coords", {})),
            )
            self._stations.append(station)
            self._station_by_id[st_id] = station
            self._station_compartment_names[st_id] = self._compartment_by_id[comp_id].name

            # Pre-parse OT passages
            ot_parsed: list[tuple[str, int, int, int]] = []
            for ref_str in station.ot_passages:
                p = parse_passage_ref(ref_str)
                if p:
                    osis, chap, start_v, end_v = p
                    ns, ne = _normalize_range(start_v, end_v)
                    ot_parsed.append((osis, chap, ns, ne))
            self._ot_ranges[st_id] = ot_parsed

            # Pre-parse NT passages
            nt_parsed: list[tuple[str, int, int, int]] = []
            for ref_str in station.nt_fulfillment:
                p = parse_passage_ref(ref_str)
                if p:
                    osis, chap, start_v, end_v = p
                    ns, ne = _normalize_range(start_v, end_v)
                    nt_parsed.append((osis, chap, ns, ne))
            self._nt_ranges[st_id] = nt_parsed

        # Services
        self._services: list[SanctuaryService] = []
        self._service_by_id: dict[str, SanctuaryService] = {}
        for srv in data.get("services", []):
            service = SanctuaryService(
                id=srv["id"],
                name=srv["name"],
                hebrew_name=srv.get("hebrew_name", ""),
                transliteration=srv.get("transliteration", ""),
                frequency=srv.get("frequency", ""),
                location=srv.get("location", ""),
                participants=srv.get("participants", ""),
                focus=srv.get("focus", ""),
                process=srv.get("process", ""),
                christological_antitype=srv.get("christological_antitype", ""),
                scriptures=list(srv.get("scriptures", [])),
            )
            self._services.append(service)
            self._service_by_id[srv["id"]] = service

        # Plan of Salvation
        self._plan_phases: list[PlanOfSalvationPhase] = []
        self._plan_by_id: dict[str, PlanOfSalvationPhase] = {}
        for phase in data.get("plan_of_salvation", []):
            p = PlanOfSalvationPhase(
                id=phase["id"],
                stage_number=int(phase.get("stage_number", 0)),
                title=phase["title"],
                symbolic_compartment=phase.get("symbolic_compartment", ""),
                symbolic_furniture=list(phase.get("symbolic_furniture", [])),
                prophetic_time=phase.get("prophetic_time", ""),
                historical_event=phase.get("historical_event", ""),
                theological_significance=phase.get("theological_significance", ""),
                biblical_anchors=list(phase.get("biblical_anchors", [])),
            )
            self._plan_phases.append(p)
            self._plan_by_id[p.id] = p

    @property
    def version(self) -> str:
        return self._version

    @property
    def title(self) -> str:
        return self._title

    @property
    def description(self) -> str:
        return self._description

    def list_compartments(self) -> list[SanctuaryCompartment]:
        return list(self._compartments)

    def get_compartment(self, comp_id: str) -> Optional[SanctuaryCompartment]:
        return self._compartment_by_id.get(comp_id)

    def list_stations(
        self,
        compartment: Optional[str] = None,
        query: Optional[str] = None,
    ) -> list[SanctuaryStation]:
        """Filter stations by compartment or search terms."""
        results = self._stations
        if compartment:
            comp_norm = compartment.strip().lower()
            results = [s for s in results if s.compartment == comp_norm]

        if query:
            q_terms = query.strip().lower().split()
            filtered = []
            for s in results:
                searchable = (
                    f"{s.name} {s.common_name} {s.hebrew_name} {s.transliteration} "
                    f"{s.theological_meaning} {s.spiritual_reality} {s.priestly_service} "
                    f"{s.sda_consensus} {' '.join(s.ot_passages)} {' '.join(s.nt_fulfillment)} "
                    f"{' '.join(s.strongs)}"
                ).lower()
                if all(term in searchable for term in q_terms):
                    filtered.append(s)
            results = filtered

        return results

    def get_station(self, station_id: str) -> Optional[SanctuaryStation]:
        return self._station_by_id.get(station_id)

    def list_services(self) -> list[SanctuaryService]:
        return list(self._services)

    def get_service(self, service_id: str) -> Optional[SanctuaryService]:
        return self._service_by_id.get(service_id)

    def list_plan_phases(self) -> list[PlanOfSalvationPhase]:
        return list(self._plan_phases)

    def get_plan_phase(self, phase_id: str) -> Optional[PlanOfSalvationPhase]:
        return self._plan_by_id.get(phase_id)

    def get_annotated_stations_for_verse(
        self,
        osis: str,
        chap: int,
        verse: int,
    ) -> list[AnnotatedSanctuaryStation]:
        """Lookup sanctuary stations linked to a specific verse via zero-allocation integer comparisons."""
        results: list[AnnotatedSanctuaryStation] = []
        for s in self._stations:
            is_ot = False
            for c_osis, c_chap, c_start, c_end in self._ot_ranges.get(s.id, []):
                if c_osis == osis and c_chap == chap and c_start <= verse <= c_end:
                    is_ot = True
                    break

            is_nt = False
            for c_osis, c_chap, c_start, c_end in self._nt_ranges.get(s.id, []):
                if c_osis == osis and c_chap == chap and c_start <= verse <= c_end:
                    is_nt = True
                    break

            if is_ot or is_nt:
                comp_name = self._station_compartment_names.get(s.id, s.compartment)
                results.append(
                    AnnotatedSanctuaryStation.from_station(
                        station=s,
                        compartment_name=comp_name,
                        is_ot=is_ot,
                        is_nt=is_nt,
                    )
                )
        return results

    def get_annotated_stations_for_passage(
        self,
        ref: str,
    ) -> list[AnnotatedSanctuaryStation]:
        """Lookup stations associated with a passage reference. Raises ValueError on malformed ref."""
        parsed = parse_passage_ref(ref)
        if not parsed:
            return []

        osis, chap, v_start, v_end = parsed
        norm_start, norm_end = _normalize_range(v_start, v_end)

        results: list[AnnotatedSanctuaryStation] = []
        for s in self._stations:
            is_ot = False
            for c_osis, c_chap, c_start, c_end in self._ot_ranges.get(s.id, []):
                if c_osis == osis and c_chap == chap:
                    if max(norm_start, c_start) <= min(norm_end, c_end):
                        is_ot = True
                        break

            is_nt = False
            for c_osis, c_chap, c_start, c_end in self._nt_ranges.get(s.id, []):
                if c_osis == osis and c_chap == chap:
                    if max(norm_start, c_start) <= min(norm_end, c_end):
                        is_nt = True
                        break

            if is_ot or is_nt:
                comp_name = self._station_compartment_names.get(s.id, s.compartment)
                results.append(
                    AnnotatedSanctuaryStation.from_station(
                        station=s,
                        compartment_name=comp_name,
                        is_ot=is_ot,
                        is_nt=is_nt,
                    )
                )

        return results

    def get_all_data(self) -> dict[str, Any]:
        """Return full structured sanctuary dataset for wire payload."""
        return {
            "version": self._version,
            "title": self._title,
            "description": self._description,
            "compartments": [c.to_dict() for c in self._compartments],
            "stations": [s.to_dict() for s in self._stations],
            "services": [srv.to_dict() for srv in self._services],
            "plan_of_salvation": [p.to_dict() for p in self._plan_phases],
        }


_INSTANCE: Optional[SanctuaryEngine] = None
_LOCK = threading.Lock()


def get_sanctuary_engine() -> SanctuaryEngine:
    """Singleton getter for thread-safe SanctuaryEngine."""
    global _INSTANCE
    if _INSTANCE is None:
        with _LOCK:
            if _INSTANCE is None:
                _INSTANCE = SanctuaryEngine()
    return _INSTANCE
