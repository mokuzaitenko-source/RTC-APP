from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional


@dataclass
class Dev2ExecutionResult:
    applied: bool
    files_changed: List[str]
    patch_handle: Optional[Any]
    error: Optional[str] = None


ApplyFn = Callable[..., Any]
ValidateEditsFn = Callable[..., List[Dict[str, Any]]]


def apply_and_maybe_rollback(
    *,
    apply_fn: ApplyFn,
    validate_edits_fn: ValidateEditsFn,
    proposal_payload: Dict[str, Any],
    repo_root: Any,
    allow_doc_edits: bool,
    lock_gate: bool,
    dry_run: bool,
) -> Dev2ExecutionResult:
    try:
        normalized_edits = validate_edits_fn(
            edits=proposal_payload.get("edits", []),
            repo_root=repo_root,
            allow_doc_edits=allow_doc_edits,
            lock_gate=lock_gate,
        )
        if dry_run or not normalized_edits:
            files_changed = [str(edit.get("path", "")) for edit in normalized_edits]
            return Dev2ExecutionResult(applied=False, files_changed=files_changed, patch_handle=None)

        patch = apply_fn(
            repo_root=repo_root,
            proposal={**proposal_payload, "edits": normalized_edits},
            allow_doc_edits=allow_doc_edits,
            lock_gate=lock_gate,
        )
        files_changed = list(dict.fromkeys(getattr(patch, "changed_files", [])))
        return Dev2ExecutionResult(applied=True, files_changed=files_changed, patch_handle=patch)
    except Exception as exc:
        return Dev2ExecutionResult(applied=False, files_changed=[], patch_handle=None, error=str(exc))
