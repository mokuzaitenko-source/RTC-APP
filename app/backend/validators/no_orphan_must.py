from __future__ import annotations

import re
from typing import Dict, List, Set, Tuple

from .evidence import build_file_line_ref, sort_evidence
from .matrix_parser import parse_core_rows
from .rfc_normative import extract_normative_lines
from .types import EvidenceItem, InvariantResult, ValidatorContext


_REQ_TAG_RE = re.compile(r"\b(?:REQ|R)-[A-Za-z0-9.\-]+\b", re.IGNORECASE)


def _must_shall_lines(ctx: ValidatorContext):
	return [
		line
		for line in extract_normative_lines(ctx.rfc_path)
		if line.normative_level in {"MUST", "SHALL"}
	]


def _section_key(rfc_line_id: str) -> str:
	# RFC 3.2:L118 -> RFC 3.2
	return rfc_line_id.split(":L", 1)[0]


def _build_section_req_index(rows) -> Dict[str, List[str]]:
	section_index: Dict[str, Set[str]] = {}
	for row in rows:
		if not row.source_ref:
			continue
		section = _section_key(row.source_ref) if ":L" in row.source_ref else row.source_ref
		if not section.startswith("RFC "):
			continue
		section_index.setdefault(section, set()).add(row.req_id)
	return {key: sorted(values) for key, values in section_index.items()}


def _source_line_mode(rows, normative_lines) -> Tuple[list, List[str]]:
	source_refs = {row.source_ref for row in rows if row.source_ref}
	orphans = [line for line in normative_lines if line.rfc_line_id not in source_refs]
	return orphans, []


def _req_tag_strict_mode(rows, normative_lines) -> Tuple[list, List[str]]:
	req_ids = {row.req_id.upper() for row in rows}
	orphan_lines = []
	missing_req_tags: List[str] = []
	for line in normative_lines:
		tags = [match.group(0).upper() for match in _REQ_TAG_RE.finditer(line.text)]
		if not tags:
			orphan_lines.append(line)
			continue
		if not any(tag in req_ids for tag in tags):
			orphan_lines.append(line)
			missing_req_tags.extend(tags)
	return orphan_lines, sorted(set(missing_req_tags))


def _hybrid_suggestions(rows, orphan_lines) -> List[dict]:
	section_index = _build_section_req_index(rows)
	suggestions: List[dict] = []
	for line in orphan_lines:
		candidates = section_index.get(_section_key(line.rfc_line_id), [])
		suggestions.append(
			{
				"rfc_line_id": line.rfc_line_id,
				"suggested_req_ids": candidates[:3],
			}
		)
	return suggestions


def check(ctx: ValidatorContext) -> InvariantResult:
	rows = parse_core_rows(ctx.matrix_path)
	normative_lines = _must_shall_lines(ctx)
	mode = (ctx.orphan_mapping_mode or "source_line").strip().lower()
	if mode not in {"source_line", "hybrid", "req_tag_strict"}:
		mode = "source_line"

	if mode == "req_tag_strict":
		orphans, missing_req_tags = _req_tag_strict_mode(rows, normative_lines)
	else:
		# Hybrid mode intentionally preserves source-line pass/fail behavior in v1.
		orphans, missing_req_tags = _source_line_mode(rows, normative_lines)

	orphan_ids = [line.rfc_line_id for line in orphans]
	evidence_items: List[EvidenceItem] = []
	if orphan_ids:
		evidence_items.append(
			EvidenceItem(
				kind="id_list",
				ref="orphan_must",
				detail=f"missing={sorted(orphan_ids)}; extra=[]",
			)
		)
		first = orphans[0]
		evidence_items.append(
			EvidenceItem(
				kind="file_line",
				ref=build_file_line_ref(
					ctx.rfc_path,
					first.line_number,
					workspace_root=ctx.workspace_root,
				),
				detail=first.text,
				hash=first.hash,
			)
		)

	if missing_req_tags:
		evidence_items.append(
			EvidenceItem(
				kind="id_list",
				ref="missing_req_tags",
				detail=f"missing={missing_req_tags}; extra=[]",
			)
		)

	evidence = sort_evidence(evidence_items)
	suggested_matches = _hybrid_suggestions(rows, orphans) if mode == "hybrid" and orphans else None
	if not orphan_ids:
		return InvariantResult(
			id="no_orphan_must",
			status="pass",
			message="All RFC MUST/SHALL lines map to core matrix rows.",
			evidence=evidence,
			recommended_action="",
			suggested_matches=suggested_matches,
		)

	return InvariantResult(
		id="no_orphan_must",
		status="fail",
		message="RFC MUST/SHALL lines missing core matrix mapping.",
		evidence=evidence,
		recommended_action="map_orphans",
		suggested_matches=suggested_matches,
	)
