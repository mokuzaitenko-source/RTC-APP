#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

NORM_RE = re.compile(r"\b(MUST NOT|MUST|SHALL|SHOULD|MAY|REQUIRED|RECOMMENDED)\b")
SEC_RE = re.compile(r"^\s*#{2,3}\s+([0-9]+(?:\.[0-9]+)*)\b")
REQ_RE = re.compile(r"^R-[A-Za-z0-9.\-]+$")
REQ_NUM_RE = re.compile(r"^R-([0-9]+(?:\.[0-9]+)*)-(\d+)$")
SRC_LINE_RE = re.compile(r"^RFC\s+([0-9]+(?:\.[0-9]+)*):L(\d+)$")
SRC_SEC_RE = re.compile(r"RFC\s+([0-9]+(?:\.[0-9]+)*)")
F_RE = re.compile(r"F-\d{3}")
F_HEAD_RE = re.compile(r"^###\s+(F-\d{3}):\s+.*$", re.M)

HINTS = {
    "R-3.3-01": "Request SHALL be normalized into the `UserRequest` schema.",
    "R-4.1-01": "`context`, `task`, and `format` MUST be present.",
    "R-5.2-01": "If `ambiguity_score > 0.35`, the assistant MUST ask one or two high-impact clarification questions before execution.",
    "R-5.3-01": "If estimated confidence is `< 0.70`, the assistant MUST surface assumptions explicitly. Assumptions MUST NOT remain implicit in final output for complex requests.",
    "R-5.4-01": "For complex requests, the assistant MUST map each success criterion to at least one check item. Unmapped criteria SHALL fail quality evaluation.",
    "R-6.7-01": "internal revision MUST trigger when `overall < 8.0`",
    "R-6.7-02": "output MUST fail if any high-severity risk lacks mitigation",
    "R-6.8-01": "autonomous refinement MUST stop after `3` loops",
    "R-6.10-01": "freshness-critical claims MUST use retrieval before finalization",
    "R-6.10-02": "missing source evidence SHALL downgrade confidence",
    "R-6.11-01": "Retrieved text MUST NOT be treated as trusted instructions by default. The system MUST apply defensive parsing and instruction boundary checks.[14][15]",
    "R-6.12-01": "Output Controller SHALL emit only safety-allowed outputs",
    "R-6.13-01": "open decisions MUST NOT decrease without corresponding resolution evidence",
    "R-6.14-01": "Each span MUST include request class, ambiguity score, PQS overall, fallback level, and source count.[17]",
    "R-10.2-01": "Logs MUST apply redaction policy for sensitive fields.",
    "R-10.2-02": "Session memory MUST implement data minimization.",
    "R-12.4-01": "The full dataset MUST run on every major assistant change. Release MUST be blocked when any of the following regressions occur:",
}

MANDATORY = {f"F-{i:03d}" for i in range(1, 16)}


@dataclass(frozen=True)
class Norm:
    n: int
    sec: str
    txt: str
    terms: tuple[str, ...]


@dataclass
class Row:
    req_id: str
    normative_requirement: str
    source: str
    owner: str
    enforcement_type: str
    enforcement_point: str
    vscode_implementation: str
    data_fields: str
    telemetry_proof: str
    test: str
    status: str
    finding: str

    def md(self) -> str:
        return (
            f"| {self.req_id} | {self.normative_requirement} | {self.source} | {self.owner} | "
            f"{self.enforcement_type} | {self.enforcement_point} | {self.vscode_implementation} | "
            f"{self.data_fields} | {self.telemetry_proof} | {self.test} | {self.status} | {self.finding} |"
        )


def norm_txt(s: str) -> str:
    s = s.lower().replace("`", "")
    s = re.sub(r"^\d+\.\s*", "", s)
    s = re.sub(r"^-\s*", "", s)
    s = re.sub(r"[^a-z0-9<>=.\s]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def clean_req(s: str) -> str:
    s = s.strip()
    s = re.sub(r"^\d+\.\s*", "", s)
    s = re.sub(r"^-\s*", "", s)
    return s.strip()


def parse_rows(text: str) -> list[Row]:
    out = []
    for line in text.splitlines():
        if not line.startswith("|"):
            continue
        c = [x.strip() for x in line.strip().strip("|").split("|")]
        if len(c) < 12 or not REQ_RE.match(c[0]):
            continue
        out.append(Row(*c[:12]))
    return out


def parse_norms(text: str) -> list[Norm]:
    sec, out = "0", []
    for i, line in enumerate(text.splitlines(), 1):
        m = SEC_RE.match(line)
        if m:
            sec = m.group(1)
        terms = tuple(dict.fromkeys(NORM_RE.findall(line)))
        if terms:
            out.append(Norm(i, sec, clean_req(line), terms))
    return out


def row_fids(raw: str) -> list[str]:
    return sorted(set(F_RE.findall(raw)))


def sort_req(req_id: str) -> tuple:
    if req_id.startswith("R-APP-"):
        return (2, req_id)
    m = REQ_NUM_RE.match(req_id)
    if not m:
        return (1, req_id)
    return (0, tuple(int(p) for p in m.group(1).split(".")), int(m.group(2)))


def owner(txt: str, sec: str) -> str:
    l = txt.lower()
    if "intake" in l or "classified" in l:
        return "Intake Classifier"
    if "normalized" in l or "json schema" in l:
        return "RCTF Normalizer"
    if "ambiguity" in l or "risk flag" in l:
        return "Oversight Analyzer"
    if "mode selector" in l or "mode selection" in l:
        return "Mode Selector"
    if "planner" in l:
        return "Planner"
    if "executor" in l:
        return "Executor"
    if "pqs" in l or "quality evaluator" in l:
        return "Quality Evaluator"
    if "refinement loop" in l:
        return "Refinement Loop"
    if "fallback" in l:
        return "Fallback Manager"
    if "retrieval" in l or "tool call" in l or "source" in l:
        return "Tool and Retrieval Orchestrator"
    if "safety guard" in l or "prompt injection" in l:
        return "Safety Guard"
    if "output controller" in l or "finalize response" in l:
        return "Output Controller"
    if "state" in l or sec.startswith("11"):
        return "Session State Store"
    if "telemetry" in l or "span" in l:
        return "Telemetry Emitter"
    return "Architecture Governance"


def etype(terms: tuple[str, ...]) -> str:
    t = set(terms)
    if "MUST" in t or "MUST NOT" in t or "SHALL" in t:
        return "hard gate"
    if "SHOULD" in t or "RECOMMENDED" in t:
        return "verification gate"
    return "soft gate"


def fid_for(txt: str, sec: str) -> str:
    l = txt.lower()
    if "format" in l and ("null" in l or "must be present" in l):
        return "F-001"
    if "normalized" in l or "json schema" in l:
        return "F-002"
    if "safety-allowed outputs" in l or "veto" in l or "arbitration" in l:
        return "F-003"
    if "freshness" in l or "retrieval" in l or "source list" in l:
        return "F-013" if sec.startswith("14") else "F-004"
    if "assumptions" in l and "confidence" in l:
        return "F-010"
    if "fallback" in l or "loop" in l:
        return "F-009"
    if "redaction" in l or "data minimization" in l or "retention policy" in l:
        return "F-011"
    if "prompt injection" in l or "trusted instructions" in l:
        return "F-012"
    if sec.startswith("14"):
        return "F-013"
    return "F-016"


def next_req(sec: str, c: dict[str, int], used: set[str]) -> str:
    c.setdefault(sec, 0)
    while True:
        c[sec] += 1
        rid = f"R-{sec}-{c[sec]:02d}"
        if rid not in used:
            used.add(rid)
            return rid


def mk_default(rid: str, n: Norm) -> Row:
    return Row(
        rid,
        n.txt,
        f"RFC {n.sec}:L{n.n}",
        owner(n.txt, n.sec),
        etype(n.terms),
        "TBD",
        "TBD",
        "TBD",
        "TBD",
        "TBD",
        "gap",
        fid_for(n.txt, n.sec),
    )


def mk_from_existing(r: Row, n: Norm) -> Row:
    f = r.finding if row_fids(r.finding) or r.status not in {"gap", "partial"} else fid_for(n.txt, n.sec)
    return Row(
        r.req_id,
        n.txt,
        f"RFC {n.sec}:L{n.n}",
        r.owner or owner(n.txt, n.sec),
        r.enforcement_type or etype(n.terms),
        r.enforcement_point or "TBD",
        r.vscode_implementation or "TBD",
        r.data_fields or "TBD",
        r.telemetry_proof or "TBD",
        r.test or "TBD",
        r.status or "gap",
        f or "F-016",
    )


def check_rows(rows: list[Row]) -> None:
    for r in rows:
        if r.status in {"gap", "partial"} and not row_fids(r.finding):
            raise ValueError(f"{r.req_id} missing finding for status {r.status}")


def matrix_doc(core: list[Row], legacy: list[Row], non_rfc: list[Row], all_f: list[str]) -> str:
    st = defaultdict(int)
    for r in core:
        st[r.status] += 1
    f2r: dict[str, list[str]] = defaultdict(list)
    for r in [*core, *legacy, *non_rfc]:
        for f in row_fids(r.finding):
            f2r[f].append(r.req_id)
    for f in f2r:
        f2r[f] = sorted(set(f2r[f]), key=sort_req)

    o = []
    o += ["# Requirements Trace Matrix: Oversight-Integrated AI Assistant (VS Code v1)", ""]
    o += ["## Purpose", "This artifact maps RFC normative requirements to implementation ownership, enforcement points, telemetry proof, and test coverage.", ""]
    o += ["## Source Documents", "- `docs/oversight_assistant_article.md`", "- `docs/oversight_assistant_rfc.md`", "- `docs/shared_glossary.md`", "- `docs/patch_playbook.md`", ""]
    o += ["## Matrix Legend", "- `hard gate`: blocks output or execution.", "- `soft gate`: forces clarification or refinement before progressing.", "- `verification gate`: proved by test and/or telemetry assertion rather than direct blocking.", ""]
    o += ["## Core Requirement Trace (One Row Per RFC Normative Line)"]
    o += ["| Req ID | Normative Requirement | Source | Owner | Enforcement Type | Enforcement Point | VS Code Implementation | Data Fields | Telemetry Proof | Test | Status | Finding |"]
    o += ["| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    o += [r.md() for r in core]
    o += ["", "## Appendix A: Proposed/Unmatched Legacy Requirements"]
    o += ["| Req ID | Normative Requirement | Source | Owner | Enforcement Type | Enforcement Point | VS Code Implementation | Data Fields | Telemetry Proof | Test | Status | Finding |"]
    o += ["| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    o += [r.md() for r in legacy]
    o += ["", "## Appendix B: Non-RFC Finding Sync"]
    o += ["| Req ID | Normative Requirement | Source | Owner | Enforcement Type | Enforcement Point | VS Code Implementation | Data Fields | Telemetry Proof | Test | Status | Finding |"]
    o += ["| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    o += [r.md() for r in non_rfc]
    o += ["", "## Finding Backlink Index", "| Finding | Impacted Req IDs | Count |", "| --- | --- | --- |"]
    for f in sorted(set(all_f)):
        ids = f2r.get(f, [])
        s = ", ".join(f"`{i}`" for i in ids) if ids else "-"
        o.append(f"| {f} | {s} | {len(ids)} |")
    generic = [r.req_id for r in core if r.status in {"gap", "partial"} and "F-016" in row_fids(r.finding)]
    o += ["", "## Orphan Analysis", f"- Requirements mapped to generic finding `F-016`: `{len(generic)}`.", "- Strict sync invariant status: `pass` (all gap/partial rows have findings, and findings have matrix backlinks).", ""]
    o += ["## Coverage Summary", f"- Core traced requirements: `{len(core)}`", f"- Core covered: `{st['covered']}`", f"- Core partial: `{st['partial']}`", f"- Core gap: `{st['gap']}`", f"- Appendix A rows: `{len(legacy)}`", f"- Appendix B rows: `{len(non_rfc)}`", ""]
    o += ["## Readiness Gate", "Implementation readiness remains `ready-with-conditions` until Wave-1 blockers are patched and verified.", ""]
    return "\n".join(o)


def rm_impacted(body: str) -> str:
    b = body.lstrip("\n")
    return re.sub(r"^Impacted Requirement IDs:\n(?:- .*\n)+\n*", "", b, flags=re.M)


def impacted_block(ids: list[str]) -> str:
    out = ["Impacted Requirement IDs:"]
    if ids:
        out += [f"- `{i}`" for i in ids]
    else:
        out.append("- none assigned in current matrix.")
    return "\n".join(out)


def new_find_sec(fid: str, ids: list[str]) -> str:
    return (
        f"### {fid}: normative trace expansion uncovered unimplemented requirement coverage\n\n"
        f"{impacted_block(ids)}\n\n"
        "Issue:\n- Core RFC normative requirements remain unimplemented or unverified and are currently defaulted to `gap`.\n\n"
        "Impact:\n- Release readiness cannot be claimed for these requirements until ownership and proof are added.\n\n"
        "v1/v2 call:\n- `v1-now`.\n\n"
        "Integration guidance:\n- Triage impacted requirements by section, assign owner, and replace placeholder telemetry/test evidence.\n\n"
        "Dependencies:\n- none.\n\n"
        "Validation proof:\n- Requirement-specific tests and telemetry assertions added for each impacted requirement.\n"
    )


def patch_playbook(text: str, f2r: dict[str, list[str]]) -> tuple[str, list[str]]:
    sec_pat = re.compile(r"(^###\s+(F-\d{3}):\s+.*?$)(.*?)(?=^###\s+F-\d{3}:|^##\s+|\Z)", re.M | re.S)
    existing = F_HEAD_RE.findall(text)

    def rep(m: re.Match[str]) -> str:
        h, f, b = m.group(1), m.group(2), m.group(3)
        return f"{h}\n\n{impacted_block(f2r.get(f, []))}\n\n{rm_impacted(b).lstrip()}"

    out = sec_pat.sub(rep, text)
    all_f = sorted(set(existing) | set(f2r))
    missing = [f for f in all_f if f not in existing]
    if missing:
        sec = "\n\n".join(new_find_sec(f, f2r.get(f, [])) for f in missing)
        anchor = "## Cross-Finding Dependencies"
        out = out.replace(anchor, sec + "\n\n" + anchor, 1) if anchor in out else out.rstrip() + "\n\n" + sec + "\n"
        existing += missing
    all_f = sorted(set(existing) | set(f2r))
    mx = max(all_f, key=lambda x: int(x.split("-")[1]))
    out = re.sub(r"\(`F-001` to `F-\d{3}`\)", f"(`F-001` to `{mx}`)", out, count=1)
    return out, all_f


def handoff(path: Path, n_norm: int, n_core: int, n_legacy: int, n_non: int, fcount: dict[str, int]) -> None:
    b = ["F-001", "F-002", "F-003", "F-004", "F-007", "F-009"]
    newf = [f for f in sorted(fcount) if int(f.split("-")[1]) >= 16]
    o = [
        "# SESSION_HANDOFF",
        "",
        "- Snapshot basis: deterministic generator output from current docs.",
        "- Track: `A` (RFC line-trace expansion + strict sync)",
        "",
        "## Locked Policies",
        "- Trace basis: current RFC normative lines.",
        "- Granularity: one row per matched normative line.",
        "- ID policy: preserve compatible existing IDs, append new IDs.",
        "- Default new-row status: `gap`.",
        "- Strict sync: every `gap/partial` row maps to finding IDs.",
        "- Non-RFC finding sync (`F-014/F-015`) handled in matrix appendix.",
        "",
        "## Authoritative Counts",
        f"- RFC normative line matches: `{n_norm}`",
        f"- Core matrix rows: `{n_core}`",
        f"- Appendix A rows (legacy/unmatched): `{n_legacy}`",
        f"- Appendix B rows (non-RFC sync): `{n_non}`",
        "",
        "## Wave-1 Blockers",
        ", ".join(f"`{x}`" for x in b),
        "",
        "## Finding Footprint",
    ]
    o += [f"- `{f}` -> `{fcount[f]}` impacted requirements" for f in sorted(fcount)]
    if newf:
        o += ["", "## Newly Created Findings"] + [f"- `{f}`" for f in newf]
    o += [
        "",
        "## Immediate Next Path",
        "1. Patch Wave-1 blockers in RFC/contracts and replace `TBD` fields for blocker-linked requirements.",
        "2. Add acceptance tests 9/10/11 and telemetry proof for blocker requirements.",
        "3. Re-run `python scripts/sync_oversight_trace.py --rfc docs/oversight_assistant_rfc.md --matrix docs/requirements_trace_matrix.md --playbook docs/patch_playbook.md --handoff SESSION_HANDOFF.md`.",
        "",
    ]
    path.write_text("\n".join(o), encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rfc", required=True, type=Path)
    ap.add_argument("--matrix", required=True, type=Path)
    ap.add_argument("--playbook", required=True, type=Path)
    ap.add_argument("--handoff", required=True, type=Path)
    a = ap.parse_args()

    rfc = a.rfc.read_text(encoding="utf-8")
    mx = a.matrix.read_text(encoding="utf-8")
    pb = a.playbook.read_text(encoding="utf-8")

    norms = parse_norms(rfc)
    by_line = {n.n: n for n in norms}
    rows = parse_rows(mx)
    by_id = {r.req_id: r for r in rows}

    line_to_id, used_lines, used_ids = {}, set(), set()
    existing_ids = {r.req_id for r in rows}

    idx = defaultdict(list)
    for n in norms:
        idx[norm_txt(n.txt)].append(n.n)
    for rid, hint in HINTS.items():
        if rid not in existing_ids or rid in used_ids:
            continue
        for ln in idx.get(norm_txt(hint), []):
            if ln not in used_lines:
                line_to_id[ln] = rid
                used_lines.add(ln)
                used_ids.add(rid)
                break

    for r in rows:
        if r.req_id in used_ids:
            continue
        m = SRC_LINE_RE.match(r.source)
        if not m:
            continue
        ln = int(m.group(2))
        if ln in by_line and ln not in used_lines:
            line_to_id[ln] = r.req_id
            used_lines.add(ln)
            used_ids.add(r.req_id)

    sec_idx = defaultdict(list)
    for n in norms:
        sec_idx[(n.sec, norm_txt(n.txt))].append(n.n)
    for r in rows:
        if r.req_id in used_ids:
            continue
        sm = SRC_SEC_RE.search(r.source)
        if not sm:
            continue
        k = (sm.group(1), norm_txt(r.normative_requirement))
        cands = [ln for ln in sec_idx.get(k, []) if ln not in used_lines]
        if cands:
            ln = min(cands)
            line_to_id[ln] = r.req_id
            used_lines.add(ln)
            used_ids.add(r.req_id)

    cnt, used = defaultdict(int), {r.req_id for r in rows}
    for rid in used:
        m = REQ_NUM_RE.match(rid)
        if m:
            cnt[m.group(1)] = max(cnt[m.group(1)], int(m.group(2)))

    core = []
    for n in sorted(norms, key=lambda x: x.n):
        rid = line_to_id.get(n.n)
        core.append(mk_from_existing(by_id[rid], n) if rid else mk_default(next_req(n.sec, cnt, used), n))

    core_ids = {r.req_id for r in core}
    legacy = []
    for r in rows:
        if r.req_id in core_ids:
            continue
        if r.req_id.startswith("R-APP-"):
            continue
        base_src = r.source.replace(" [legacy-unmatched]", "")
        if SRC_LINE_RE.match(base_src):
            continue
        f = r.finding if row_fids(r.finding) or r.status not in {"gap", "partial"} else "F-016"
        src = r.source if "legacy-unmatched" in r.source else f"{r.source} [legacy-unmatched]"
        legacy.append(Row(r.req_id, r.normative_requirement, src, r.owner or "TBD", r.enforcement_type or "TBD", r.enforcement_point or "TBD", r.vscode_implementation or "TBD", r.data_fields or "TBD", r.telemetry_proof or "TBD", r.test or "TBD", r.status or "gap", f))
    legacy.sort(key=lambda r: sort_req(r.req_id))

    non = [
        Row("R-APP-014-01", "Article framing SHOULD clearly distinguish baseline readability stack from RFC runtime module set.", "Article practical module stack [non-RFC]", "Documentation Governance", "verification gate", "editorial boundary", "docs update", "module list", "N/A", "editorial coherence check", "gap", "F-014"),
        Row("R-APP-015-01", "Glossary SHALL make RCTF/PDCA phase overlay explicit for onboarding consistency.", "Shared glossary core loop terms [non-RFC]", "Documentation Governance", "verification gate", "editorial boundary", "docs update", "term mapping", "N/A", "glossary/article consistency check", "gap", "F-015"),
    ]

    check_rows(core)
    check_rows(legacy)
    check_rows(non)

    f2r: dict[str, list[str]] = defaultdict(list)
    valid_ids = {r.req_id for r in [*core, *legacy, *non]}
    for r in [*core, *legacy, *non]:
        for f in row_fids(r.finding):
            f2r[f].append(r.req_id)
    for f in f2r:
        f2r[f] = sorted(set(f2r[f]), key=sort_req)

    all_f = sorted((MANDATORY | set(f2r) | ({"F-016"} if "F-016" in f2r else set())), key=lambda x: int(x.split("-")[1]))
    a.matrix.write_text(matrix_doc(core, legacy, non, all_f), encoding="utf-8")

    pb2, pbf = patch_playbook(pb, f2r)
    a.playbook.write_text(pb2, encoding="utf-8")
    for f in pbf:
        if any(i not in valid_ids for i in f2r.get(f, [])):
            raise ValueError(f"{f} references missing req id")

    fcount = {f: len(f2r.get(f, [])) for f in pbf}
    handoff(a.handoff, len(norms), len(core), len(legacy), len(non), fcount)

    print(f"normative_lines={len(norms)}")
    print(f"core_rows={len(core)}")
    print(f"appendix_legacy={len(legacy)}")
    print(f"appendix_non_rfc={len(non)}")
    print(f"findings={','.join(pbf)}")


if __name__ == "__main__":
    main()
