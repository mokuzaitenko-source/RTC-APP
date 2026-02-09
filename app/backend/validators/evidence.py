# app/backend/validators/evidence.py
from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable, List, Optional

from .types import EvidenceItem


_FILE_LINE_RE = re.compile(r"^(.*):L(\d+)$")


def sort_evidence(items: Iterable[EvidenceItem]) -> List[EvidenceItem]:
	def key(item: EvidenceItem):
		kind_order = {
			"file_line": 0,
			"id_list": 1,
			"diff": 2,
			"summary": 3,
		}
		order = kind_order.get(item.kind, 9)
		if item.kind == "file_line":
			match = _FILE_LINE_RE.match(item.ref)
			if match:
				path, line = match.group(1), int(match.group(2))
				return (order, path, line)
			return (order, item.ref, 10**9)
		if item.kind in {"id_list", "diff"}:
			return (order, item.ref)
		return (order, item.ref)

	return sorted(list(items), key=key)


def build_file_line_ref(path: str, line_number: int, workspace_root: Optional[str] = None) -> str:
	ref_path = Path(path)
	if workspace_root:
		try:
			ref_path = ref_path.relative_to(Path(workspace_root))
		except ValueError:
			pass
	return f"{ref_path.as_posix()}:L{line_number}"

