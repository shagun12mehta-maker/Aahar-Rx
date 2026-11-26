"""Indian brand-to-salt lookup, OCR error correction, and manual search fallback."""

from __future__ import annotations

from functools import lru_cache
import json
from pathlib import Path
import re
from typing import Any

from rapidfuzz import fuzz

from .constants import DATA_DIR
from .models import ManualSearchHit, ResolvedMedication

_OCR_CORRECTIONS = str.maketrans({"0": "O", "1": "I", "5": "S", "8": "B", "|": "I", "$": "S"})

_STRENGTH_RE = re.compile(
    r"(\d+(?:\.\d+)?)\s*(mg|mcg|ug|iu|gm|g|ml)\b",
    re.IGNORECASE,
)

_GLUED_UNIT_OCR_RE = re.compile(
    r"(\d)\s*([OoIl])(?=[OoIl]*\s*(?:MG|MCG|UG|IU|GM|ML)\b)",
    re.IGNORECASE,
)

_ALPHA_DIGIT_SPLIT_RE = re.compile(r"(?<=[A-Z])(?=\d)|(?<=\d)(?=[A-Z])")

_BOILERPLATE_RE = re.compile(
    r"\b(?:IP|BP|USP|TABLETS?|CAPSULES?|FILM\s+COATED|GASTRO\s+RESISTANT|PROLONGED\s+RELEASE|"
    r"EXTENDED\s+RELEASE|SUSTAINED\s+RELEASE|EACH\s+UNCOATED|COMPOSITION|CONTAINS|"
    r"STORE\s+IN\s+A\s+COOL|RX|SCHEDULE\s+H|M\.?R\.?P\.?|BATCH|EXP|MFG)\b",
    re.IGNORECASE,
)


def _clean_text(text: str) -> str:
    upper = re.sub(r"[^A-Z0-9\s\+\-\.]", " ", text.upper())
    # Fix OCR digit/letter confusion glued to units before alpha-digit splitting inserts spaces.
    fixed_units = upper
    while True:
        updated = _GLUED_UNIT_OCR_RE.sub(
            lambda m: m.group(1) + ("0" if m.group(2).upper() == "O" else "1"),
            fixed_units,
        )
        if updated == fixed_units:
            break
        fixed_units = updated
    spaced = _ALPHA_DIGIT_SPLIT_RE.sub(" ", fixed_units)
    return re.sub(r"\s+", " ", spaced).strip()


def _ocr_normalize(text: str) -> str:
    cleaned = _clean_text(text)
    tokens = []
    for tok in cleaned.split():
        if any(c.isalpha() for c in tok) and not re.fullmatch(r"(?:MG|MCG|UG|IU|GM|ML)", tok):
            tokens.append(tok.translate(_OCR_CORRECTIONS))
        else:
            tokens.append(tok)
    return " ".join(tokens)


def extract_strength(text: str) -> str | None:
    """Extract tablet/capsule dosage strength string from strip text if present."""
    cleaned = _clean_text(text)
    matches = _STRENGTH_RE.findall(cleaned)
    if not matches:
        return None
    if len(matches) >= 2 and "+" in cleaned:
        return f"{matches[0][0]} {matches[0][1].lower()} + {matches[1][0]} {matches[1][1].lower()}"
    return f"{matches[0][0]} {matches[0][1].lower()}"


@lru_cache(maxsize=4)
def load_brand_directory(path: Path | None = None) -> list[dict[str, Any]]:
    """Load the Indian brand-to-salt directory from disk."""
    target = path or (DATA_DIR / "indian_brand_to_salt.json")
    payload = json.loads(target.read_text(encoding="utf-8"))
    return payload["entries"]


class SaltResolver:
    """Resolves noisy medicine strip OCR text to active chemical salts and drug classes."""

    def __init__(self, directory_path: Path | None = None) -> None:
        self.entries = load_brand_directory(directory_path)

    def resolve_from_ocr_text(
        self,
        raw_text: str,
        engine_name: str | None = None,
        min_confidence: float = 0.65,
    ) -> tuple[list[ResolvedMedication], bool]:
        """Resolve OCR text into ranked medications; returns (results, needs_manual_fallback)."""
        if not raw_text or not raw_text.strip():
            return [], True

        cleaned_raw = _clean_text(raw_text)
        normalized = _ocr_normalize(_BOILERPLATE_RE.sub(" ", cleaned_raw))
        strength = extract_strength(raw_text)

        candidates: dict[str, tuple[float, ResolvedMedication]] = {}

        for entry in self.entries:
            brand_id = entry["brand_id"]
            brand_name = entry["brand_name"]
            aliases = [brand_name.upper(), *[a.upper() for a in entry.get("brand_aliases", [])]]
            salt_aliases = [
                *[s.upper() for s in entry["active_salts"]],
                *[sa.upper() for sa in entry.get("salt_aliases", [])],
            ]

            best_score = 0.0
            source = "ocr_fuzzy"

            for alias in aliases:
                alias_norm = _ocr_normalize(alias)
                if re.search(rf"\b{re.escape(alias)}\b", cleaned_raw):
                    best_score = max(best_score, 0.97)
                    source = "ocr_exact"
                elif re.search(rf"\b{re.escape(alias_norm)}\b", normalized):
                    best_score = max(best_score, 0.92)
                    source = "ocr_fuzzy"

            for salt_alias in salt_aliases:
                salt_norm = _ocr_normalize(salt_alias)
                if len(salt_norm) >= 5 and (
                    salt_alias in cleaned_raw or salt_norm in normalized
                ):
                    score = 0.93
                    if score > best_score:
                        best_score = score
                        source = "salt_direct"

            if best_score < 0.90 and normalized:
                for alias in aliases:
                    alias_norm = _ocr_normalize(alias)
                    if len(alias_norm) < 4:
                        continue
                    ratio = fuzz.partial_ratio(alias_norm, normalized) / 100.0
                    token_ratio = fuzz.token_set_ratio(alias_norm, normalized) / 100.0
                    fuzzy_score = 0.65 * ratio + 0.35 * token_ratio
                    if len(alias_norm) <= 5:
                        fuzzy_score *= 0.92
                    if fuzzy_score > best_score:
                        best_score = fuzzy_score
                        source = "ocr_fuzzy"

                for salt_alias in salt_aliases:
                    salt_norm = _ocr_normalize(salt_alias)
                    if len(salt_norm) < 7:
                        continue
                    ratio = fuzz.partial_ratio(salt_norm, normalized) / 100.0
                    if ratio * 0.95 > best_score:
                        best_score = ratio * 0.95
                        source = "salt_direct"

            if best_score >= min_confidence:
                dedup_key = (
                    brand_id
                    if source in ("ocr_exact", "ocr_fuzzy")
                    else f"salt:{'|'.join(entry['active_salts'])}"
                )
                med = ResolvedMedication(
                    brand_name=brand_name
                    if source != "salt_direct"
                    else f"{entry['active_salts'][0]} (Generic / Salt Match)",
                    active_salts=list(entry["active_salts"]),
                    strength_text=strength
                    or (entry["common_strengths"][0] if entry.get("common_strengths") else None),
                    drug_class=entry["drug_class"],
                    resolution_source=source,  # type: ignore[arg-type]
                    ocr_engine_used=engine_name,
                    confidence=round(min(best_score, 0.99), 3),
                    confirmed_by_user=False,
                )
                prev = candidates.get(dedup_key)
                if prev is None or med.confidence > prev[0]:
                    candidates[dedup_key] = (med.confidence, med)

        ranked = [
            item[1]
            for item in sorted(candidates.values(), key=lambda pair: pair[0], reverse=True)
        ]
        top_salts = {tuple(m.active_salts) for m in ranked if m.resolution_source != "salt_direct"}
        filtered = [
            m
            for m in ranked
            if not (m.resolution_source == "salt_direct" and tuple(m.active_salts) in top_salts)
        ]
        results = filtered[:3]
        needs_fallback = len(results) == 0 or results[0].confidence < 0.78
        return results, needs_fallback

    def build_manual_medication(
        self,
        brand_id_or_name: str,
        strength_text: str | None = None,
        intended_dose_time_hhmm: str | None = None,
    ) -> ResolvedMedication:
        """Construct a user-selected manual fallback medication record."""
        query = brand_id_or_name.strip().lower()
        for entry in self.entries:
            if (
                entry["brand_id"].lower() == query
                or entry["brand_name"].lower() == query
            ):
                return ResolvedMedication(
                    brand_name=entry["brand_name"],
                    active_salts=list(entry["active_salts"]),
                    strength_text=strength_text
                    or (entry["common_strengths"][0] if entry.get("common_strengths") else None),
                    drug_class=entry["drug_class"],
                    resolution_source="manual_fallback",
                    ocr_engine_used=None,
                    confidence=1.0,
                    confirmed_by_user=True,
                    intended_dose_time_hhmm=intended_dose_time_hhmm,
                )
        raise KeyError(f"Unknown brand_id or brand_name: {brand_id_or_name}")

    def search_brands_and_salts(self, query: str, limit: int = 8) -> list[ManualSearchHit]:
        """Manual brand/salt autocomplete search fallback when OCR fails or needs help."""
        q = query.strip().upper()
        if not q:
            return [
                ManualSearchHit(
                    brand_id=e["brand_id"],
                    brand_name=e["brand_name"],
                    active_salts=list(e["active_salts"]),
                    drug_class=e["drug_class"],
                    common_strengths=list(e.get("common_strengths", [])),
                    is_regional_brand=bool(e.get("is_regional_brand", False)),
                    score=1.0,
                )
                for e in self.entries[:limit]
            ]

        scored: list[tuple[float, ManualSearchHit]] = []
        for entry in self.entries:
            haystack = " ".join(
                [
                    entry["brand_name"],
                    *entry.get("brand_aliases", []),
                    *entry["active_salts"],
                    *entry.get("salt_aliases", []),
                    entry["drug_class"],
                ]
            ).upper()
            brand_upper = entry["brand_name"].upper()
            salt_upper = " ".join(entry["active_salts"]).upper()

            if brand_upper.startswith(q):
                score = 1.0
            elif q in brand_upper or q in salt_upper:
                score = 0.94
            else:
                score = max(
                    fuzz.WRatio(q, brand_upper) / 100.0,
                    fuzz.partial_ratio(q, haystack) / 100.0 * 0.92,
                )

            if score >= 0.48:
                scored.append(
                    (
                        score,
                        ManualSearchHit(
                            brand_id=entry["brand_id"],
                            brand_name=entry["brand_name"],
                            active_salts=list(entry["active_salts"]),
                            drug_class=entry["drug_class"],
                            common_strengths=list(entry.get("common_strengths", [])),
                            is_regional_brand=bool(entry.get("is_regional_brand", False)),
                            score=round(min(score, 1.0), 3),
                        ),
                    )
                )

        scored.sort(key=lambda item: item[0], reverse=True)
        return [hit for _, hit in scored[:limit]]
