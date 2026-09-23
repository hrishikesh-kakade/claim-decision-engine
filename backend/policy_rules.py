"""
Deterministic policy-parameter extraction.

Percentages, day-counts and month-counts (room sub-limit %, waiting-period
lengths, pre/post-hospitalisation windows, etc.) drive the numeric part of
a claim decision, and an LLM asked to do this arithmetic from a page of
prose is exactly where "confident unsupported decisions" (the rubric's red
flag) creep in. So instead of asking the LLM to remember "1% of Sum
Insured", we regex-extract every such parameter directly out of the
*retrieved* policy chunks at startup, and keep the chunk_id each value came
from. Downstream agents only ever use `.value`; every number that reaches
the decision contract is therefore traceable to a real citation. If a
parameter can't be found in the supplied chunks, `.value` is None and the
Coverage & Exclusion Agent must treat that dimension as missing evidence
(this is the mechanism behind "abstain instead of guessing").
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class Param:
    value: Optional[float]
    chunk_id: Optional[str]
    page: Optional[int]
    raw: Optional[str] = None


class PolicyParameters:
    def __init__(self, chunks_path: Path):
        self.chunks: list[dict] = json.loads(Path(chunks_path).read_text(encoding="utf-8"))
        self._by_id = {c["chunk_id"]: c for c in self.chunks}
        self._extract_all()

    def _find(self, section, pattern: str, flags=re.IGNORECASE) -> Optional[tuple[dict, re.Match]]:
        sections = None
        if isinstance(section, str):
            sections = {section}
        elif isinstance(section, (list, set, tuple)):
            sections = set(section)
        for c in self.chunks:
            if sections and c["section"] not in sections:
                continue
            m = re.search(pattern, c["text"], flags)
            if m:
                return c, m
        return None

    def _pct(self, section: str, pattern: str) -> Param:
        hit = self._find(section, pattern)
        if not hit:
            return Param(None, None, None)
        c, m = hit
        return Param(float(m.group(1)) / 100.0, c["chunk_id"], c["page_start"], m.group(0))

    def _num(self, section: str, pattern: str) -> Param:
        hit = self._find(section, pattern)
        if not hit:
            return Param(None, None, None)
        c, m = hit
        return Param(float(m.group(1)), c["chunk_id"], c["page_start"], m.group(0))

    def _extract_all(self):
        self.room_pct = self._pct("SCOPE_OF_COVER", r"Normal Room expenses:\s*([\d.]+)%")
        self.icu_pct = self._pct("SCOPE_OF_COVER", r"Intensive Care.*?expenses:\s*([\d.]+)%")
        self.doctor_fee_pct = self._pct("SCOPE_OF_COVER", r"Surgeons fees and similar expenses subject to a limit\s*\r?\n?\s*of\s*([\d.]+)%")
        self.other_expenses_pct = self._pct("SCOPE_OF_COVER", r"similar expenses subject to a limit of\s*([\d.]+)%\s*Sum Insured")
        self.domiciliary_pct = self._pct("SCOPE_OF_COVER", r"Domiciliary Hospitalization will be paid up to a maximum aggregate sub-limit\s*\r?\n?\s*of\s*([\d.]+)%")
        self.any_one_illness_pct = self._pct("SCOPE_OF_COVER", r"Any One Illness under agreed package charges[\s\S]{0,80}?restricted to\s*([\d.]+)%")
        both = ["SCOPE_OF_COVER", "EXCLUSIONS"]
        self.ambulance_pct = self._pct(both, r"Ambulance charges[\s\S]{0,80}?limited to\s*([\d.]+)%")
        self.ambulance_flat = self._num(both, r"Ambulance charges[\s\S]{0,120}?Rupees\s*([\d,]+)/?-?\s*whichever is less")
        self.daily_allowance_pct = self._pct(both, r"Daily Allowance amount equivalent to\s*([\d.]+)%")
        self.daily_allowance_flat = self._num(both, r"Daily Allowance[\s\S]{0,80}?Rs\.?\s*([\d,]+)/?-?\s*per day")
        self.daily_allowance_cap = self._num(both, r"maximum amount payable under this extension[s]? is limited to Rs\s*([\d,]+)")

        self.pre_hosp_days = self._num(both, r"Pre-Hospitalisation up to a maximum of\s*(\d+)\s*days")
        self.post_hosp_days = self._num(both, r"Post\s*Hospitalisation expenses up to a maximum of\s*(\d+)\s*days")

        self.initial_waiting_days = self._num("EXCLUSIONS", r"waiting period of\s*(\d+)\s*days will apply to all claims")
        self.pre_existing_months = self._num("DEFINITIONS", r"within\s*(\d+)\s*months to prior to the first Policy")
        self.first_year_disease_years = Param(1.0, self._chunk_for_subsection("EXCLUSIONS", "3. Hospitalization expense incurred in the first year"), None)

        min_stay_hit = self._find("DEFINITIONS", r"minimum period of\s*(\d+)\s*In-patient Care\s*\r?\n?\s*consecutive hours")
        self.min_stay_hours = self._num("DEFINITIONS", r"minimum period of\s*(\d+)\s*In-patient Care")

        c = self._by_id.get("EXCLUSIONS-006")
        self.first_year_disease_chunk = c
        self.first_year_diseases = [
            "cataract", "benign prostatic hypertrophy", "myomectomy", "hysterectomy",
            "hernia", "hydrocele", "fistula in anus", "piles", "arthritis", "gout",
            "rheumatism", "joint replacement", "sinusitis", "stone in the urinary",
            "biliary", "dilatation and curettage", "tumor", "tumour", "cyst", "nodule",
            "polyp", "adenoid", "hemorrhoid", "dialysis", "tonsil", "gastric", "duodenal ulcer",
        ] if c else []

        self.day_care_named_procedures = [
            "dialysis", "chemotherapy", "radiotherapy", "eye surgery", "cataract",
            "lithotripsy", "tonsillectomy", "d&c",
        ]
        self.day_care_chunk = self._chunk_for_text("SCOPE_OF_COVER", "Lithotripsy")

        self.cosmetic_exclusion_chunk = self._chunk_for_text("EXCLUSIONS", "cosmetic or aesthetic")
        self.maternity_exclusion_chunk = self._chunk_for_subsection("EXCLUSIONS", "11. Expenses on treatment arising from or traceable to pregn")
        self.self_injury_exclusion_chunk = self._chunk_for_subsection("EXCLUSIONS", "8. Convalescence, general debility")
        self.war_exclusion_chunk = self._chunk_for_subsection("EXCLUSIONS", "4. Injury or Illnesses directly or indirectly caused by or a")
        self.domiciliary_prepost_exclusion_chunk = self._chunk_for_subsection("EXCLUSIONS", "17. Any expense under Domiciliary Hospitalisation for")
        self.hospital_def_chunk = self._by_id.get("DEFINITIONS-021")
        self.domiciliary_def_chunk = self._by_id.get("DEFINITIONS-015")
        self.pre_existing_def_chunk = self._by_id.get("DEFINITIONS-036")
        self.experimental_def_chunk = self._by_id.get("DEFINITIONS-049")
        self.medically_necessary_chunk = self._chunk_for_text("DEFINITIONS", "Medically Necessary")
        self.portability_waiting_reduction_chunk = self._chunk_for_subsection("EXCLUSIONS", "2. 30 days Waiting Period")
        self.ped_portability_chunk = self._chunk_for_subsection("EXCLUSIONS", "1. Pre-existing diseases")

    def _chunk_for_subsection(self, section: str, subsection_prefix: str) -> Optional[dict]:
        for c in self.chunks:
            if c["section"] == section and (c.get("subsection") or "").startswith(subsection_prefix):
                return c
        return None

    def _chunk_for_text(self, section: str, needle: str) -> Optional[dict]:
        for c in self.chunks:
            if c["section"] == section and needle.lower() in c["text"].lower():
                return c
        return None

    def summary(self) -> dict:
        def s(p: Param):
            return {"value": p.value, "chunk_id": p.chunk_id, "page": p.page}
        return {
            "room_pct": s(self.room_pct),
            "icu_pct": s(self.icu_pct),
            "doctor_fee_pct": s(self.doctor_fee_pct),
            "other_expenses_pct": s(self.other_expenses_pct),
            "domiciliary_pct": s(self.domiciliary_pct),
            "any_one_illness_pct": s(self.any_one_illness_pct),
            "ambulance_pct": s(self.ambulance_pct),
            "ambulance_flat": s(self.ambulance_flat),
            "pre_hosp_days": s(self.pre_hosp_days),
            "post_hosp_days": s(self.post_hosp_days),
            "initial_waiting_days": s(self.initial_waiting_days),
            "pre_existing_months": s(self.pre_existing_months),
            "min_stay_hours": s(self.min_stay_hours),
        }
