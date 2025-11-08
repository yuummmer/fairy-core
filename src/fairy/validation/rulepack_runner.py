# src/fairy/validate/rulepack_runner.py
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from typing import Any

import pandas as pd

# Accept both names for the row-duplicates rule
CHECK_TYPES = {"dup", "unique", "enum", "range", "no_duplicate_rows"}


def _sha256(path: Path) -> str:
    h = sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _resource_matches(pattern: str, path: Path) -> bool:
    if not pattern:
        return False
    name = path.name
    if "*" in pattern:
        # Match only against the filename for MVP
        from fnmatch import fnmatch

        return fnmatch(name, pattern)
    return name == pattern


def run_rulepack(
    inputs: list[Path], rulepack: dict[str, Any], rulepack_path: Path, timestamp_iso: str
) -> dict[str, Any]:
    rp_id = rulepack.get("id", "")
    rp_ver = rulepack.get("version", "")
    resources_spec = rulepack.get("resources", []) or []

    att_inputs = []
    for p in inputs:
        try:
            att_inputs.append(
                {"path": str(p), "sha256": _sha256(p), "bytes": int(p.stat().st_size)}
            )
        except Exception:
            att_inputs.append({"path": str(p), "sha256": "", "bytes": 0})

    report: dict[str, Any] = {
        "attestation": {
            "rulepack": {"id": rp_id, "version": rp_ver, "path": str(rulepack_path)},
            "inputs": att_inputs,
            "timestamp": timestamp_iso,
        },
        "summary": {"pass": 0, "warn": 0, "fail": 0},
        "resources": [],
    }

    for path in inputs:
        # Build the rules applicable to this file
        applicable: list[dict[str, Any]] = []
        for res in resources_spec:
            pat = res.get("pattern")
            if pat and _resource_matches(pat, path):
                applicable.extend(res.get("rules", []) or [])

        if not applicable:
            continue

        df = pd.read_csv(path)
        resource_rules = []

        for r in sorted(applicable, key=lambda x: x.get("id", "")):
            rule_id = r.get("id", "")
            rtype = (r.get("type", "") or "").strip()
            severity = (r.get("severity", "fail") or "fail").lower()
            status = "PASS"
            evidence: dict[str, Any] = {}

            if rtype not in CHECK_TYPES:
                status, evidence = "FAIL", {"error": "unknown_rule_type", "type": rtype}
            else:
                try:
                    if rtype in ("dup", "no_duplicate_rows"):
                        keys = r.get("keys", [])
                        status, evidence = check_dup(df, keys, severity)
                    elif rtype == "unique":
                        cols = r.get("columns", [])
                        status, evidence = check_unique(df, cols, severity)
                    elif rtype == "enum":
                        col = r.get("column")
                        allow = r.get("allow", [])
                        normalize = r.get("normalize", {}) or {}
                        status, evidence = check_enum(df, col, allow, normalize, severity)
                    elif rtype == "range":
                        col = r.get("column")
                        mn = r.get("min", None)
                        mx = r.get("max", None)
                        inclusive = bool(r.get("inclusive", True))
                        status, evidence = check_range(df, col, mn, mx, inclusive, severity)
                except Exception as e:
                    status, evidence = "FAIL", {"error": "runtime_error", "message": str(e)}

            resource_rules.append(
                {
                    "id": rule_id,
                    "type": rtype,
                    "severity": severity,
                    "status": status,
                    "evidence": evidence,
                }
            )

        # tally summary
        for rr in resource_rules:
            if rr["status"] == "FAIL":
                report["summary"]["fail"] += 1
            elif rr["status"] == "WARN":
                report["summary"]["warn"] += 1
            else:
                report["summary"]["pass"] += 1

        # attach resource block
        res_block = {"path": str(path), "rules": resource_rules}
        report["resources"].append(res_block)

        # add row count to attestation
        for att in report["attestation"]["inputs"]:
            if att["path"] == str(path):
                att["rows"] = int(len(df))

    return report


# ---------------- Checks (1-based row indices) ----------------


def _rows_1based(rows0: list[int]) -> list[int]:
    return [int(i) + 1 for i in rows0]


def _status_from_severity(sev: str) -> str:
    return "FAIL" if (sev or "fail") == "fail" else "WARN"


def check_dup(df: pd.DataFrame, keys: list[str], severity: str) -> tuple[str, dict[str, Any]]:
    if not keys:
        return "FAIL", {"error": "config_missing_keys"}
    for k in keys:
        if k not in df.columns:
            return "FAIL", {"error": "column_not_found", "column": k}
    dup_mask = df.duplicated(subset=keys, keep="first")
    dup_rows = df.index[dup_mask].tolist()
    if dup_rows:
        return _status_from_severity(severity), {
            "duplicates": [{"rows": _rows_1based(dup_rows)}],
            "count": len(dup_rows),
        }
    return "PASS", {"count": 0}


def check_unique(df: pd.DataFrame, columns: list[str], severity: str) -> tuple[str, dict[str, Any]]:
    if not columns:
        return "FAIL", {"error": "config_missing_columns"}
    for c in columns:
        if c not in df.columns:
            return "FAIL", {"error": "column_not_found", "column": c}
    # composite unique via tuple
    series = df[columns].astype(object).apply(tuple, axis=1)
    dup_mask = series.duplicated(keep="first")
    dup_rows = df.index[dup_mask].tolist()
    if dup_rows:
        return _status_from_severity(severity), {
            "duplicates": [{"rows": _rows_1based(dup_rows)}],
            "count": len(dup_rows),
        }
    return "PASS", {"count": 0}


def _normalize(v, norm: dict[str, Any]):
    if pd.isna(v):
        return v
    s = str(v)
    if norm.get("trim", False):
        s = s.strip()
    if norm.get("casefold", False):
        s = s.casefold()
    return s


def check_enum(
    df: pd.DataFrame, column: str, allow: list[Any], normalize: dict[str, Any], severity: str
) -> tuple[str, dict[str, Any]]:
    if not column:
        return "FAIL", {"error": "config_missing_column"}
    if column not in df.columns:
        return "FAIL", {"error": "column_not_found", "column": column}
    if not isinstance(allow, list) or not allow:
        return "FAIL", {"error": "config_missing_allow"}
    # normalize allow list if requested
    norm_allow = [_normalize(a, normalize) for a in allow] if normalize else allow
    out = []
    for i, v in enumerate(df[column].tolist()):
        vv = _normalize(v, normalize or {})
        if pd.isna(vv) or vv not in norm_allow:
            out.append(i)
    if out:
        return _status_from_severity(severity), {
            "out_of_set": {"count": len(out), "rows": _rows_1based(out)}
        }
    return "PASS", {"normalized": bool(normalize)}


def check_range(
    df: pd.DataFrame, column: str, mn, mx, inclusive: bool, severity: str
) -> tuple[str, dict[str, Any]]:
    if not column:
        return "FAIL", {"error": "config_missing_column"}
    if column not in df.columns:
        return "FAIL", {"error": "column_not_found", "column": column}
    # numeric-only MVP; datetime can be added later
    series = pd.to_numeric(df[column], errors="coerce")
    out = []
    for i, val in enumerate(series.tolist()):
        if pd.isna(val):
            out.append(i)
            continue
        if mn is not None:
            if inclusive and val < mn:
                out.append(i)
            if not inclusive and val <= mn:
                out.append(i)
        if mx is not None:
            if inclusive and val > mx:
                out.append(i)
            if not inclusive and val >= mx:
                out.append(i)
    if out:
        return _status_from_severity(severity), {
            "out_of_bounds": {"count": len(out), "rows": _rows_1based(out)}
        }
    return "PASS", {"count": 0}


# ---------------- Markdown writer (deterministic order) ----------------


def write_markdown(report: dict[str, Any]) -> str:
    att = report.get("attestation", {})
    rp = att.get("rulepack", {})
    ts = att.get("timestamp", "")
    out: list[str] = []
    out += [
        "# FAIRy Validate Report",
        "",
        f"**Timestamp:** {ts}",
        f"**Rulepack:** {rp.get('id','')}@{rp.get('version','')} ({rp.get('path','')})",
        "",
        "## Summary",
        f"- PASS: {report.get('summary',{}).get('pass',0)}",
        f"- WARN: {report.get('summary',{}).get('warn',0)}",
        f"- FAIL: {report.get('summary',{}).get('fail',0)}",
        "",
        "## Inputs",
    ]
    for i in att.get("inputs", []):
        path = i.get("path", "")
        sh = i.get("sha256", "")
        rows = i.get("rows", "")
        bytes_ = i.get("bytes", "")
        out.append(f"- `{path}` — sha256={sh}, rows={rows}, bytes={bytes_}")

    out.append("")
    for res in sorted(report.get("resources", []), key=lambda r: r.get("path", "")):
        out.append(f"## Findings for `{res.get('path','')}`")
        for rr in sorted(res.get("rules", []), key=lambda r: r.get("id", "")):
            out.append(f"### [{rr.get('status')}] {rr.get('id')} — {rr.get('type')}")
            ev = rr.get("evidence", {})
            if "duplicates" in ev:
                for d in ev["duplicates"]:
                    out.append(f"Duplicates at rows {d.get('rows',[])}")
            if "out_of_set" in ev:
                o = ev["out_of_set"]
                out.append(f"Out of set rows {o.get('rows',[])} (count={o.get('count',0)})")
            if "out_of_bounds" in ev:
                o = ev["out_of_bounds"]
                out.append(f"Out of bounds rows {o.get('rows',[])} (count={o.get('count',0)})")
            if ev.get("normalized") is True:
                out.append("Normalized comparison applied.")
            if "error" in ev:
                out.append(f"Error: {ev['error']}")
        out.append("")
    return "\n".join(out)
