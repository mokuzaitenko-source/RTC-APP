# app/backend/validators/rfc_normative.py
from __future__ import annotations

import hashlib
import re
from typing import List

from .types import NormativeLine


_NORMATIVE_RE = re.compile(r"\b(MUST|SHALL|SHOULD|MAY)\b")
_SECTION_RE = re.compile(r"^\s*#{2,3}\s+([0-9]+(?:\.[0-9]+)*)\b")


def _normalize_line(text: str) -> str:
	return " ".join(text.strip().split())


def extract_normative_lines(rfc_path: str) -> List[NormativeLine]:
	results: List[NormativeLine] = []
	in_code_block = False
	section = "0"
	with open(rfc_path, "r", encoding="utf-8") as handle:
		for idx, raw in enumerate(handle.readlines(), start=1):
			line = raw.rstrip("\n")
			if line.strip().startswith("```"):
				in_code_block = not in_code_block
				continue
			if in_code_block:
				continue
			section_match = _SECTION_RE.match(line)
			if section_match:
				section = section_match.group(1)
			if line.lstrip().startswith("#"):
				continue
			match = _NORMATIVE_RE.search(line)
			if not match:
				continue
			normative_level = match.group(1)
			normalized = _normalize_line(line)
			digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
			results.append(
				NormativeLine(
					rfc_line_id=f"RFC {section}:L{idx}",
					normative_level=normative_level,
					text=normalized,
					hash=f"sha256:{digest}",
					line_number=idx,
				)
			)
	return results

