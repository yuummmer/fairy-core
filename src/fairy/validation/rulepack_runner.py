# src/fairy/validate/rulepack_runner.py
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from typing import Any

import pandas as pd

# Accept both names for the row-duplicates rule (+ foreign_key for multi-input)
CHECK_TYPES = {"dup", "unique", "enum", "range", "no_duplicate_rows", "foreign_key"}


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
    inputs_map: dict[str, Path], rulepack: dict, rp_path: Path, now_iso: str
) -> dict[str, Any]:
    """
    Validate one or more inputs using a rulepack.

    inputs_map: name -> CSV Path
      - legacy single-file mode: {"default": <file>}
      - folder/explicit multi:   {"artworks": <path>, "artists": <path>, ...}
    """
    rp_id = rulepack.get("id", "")
    rp_ver = rulepack.get("version", "")
    resources_spec = rulepack.get("resources", []) or []

    # ---- Load all inputs once (enables cross-table checks)
    frames: dict[str, pd.DataFrame] = {}
    for name, path in inputs_map.items():
        frames[name] = pd.read_csv(path)

    # ---- Attestation + metadata echo (non-breaking)
    att_inputs = []
    for name, p in inputs_map.items():
        try:
            att_inputs.append(
                {
                    "name": name,
                    "path": str(p),
                    "sha256": _sha256(p),
                    "bytes": int(p.stat().st_size),
                    "rows": int(len(frames[name])),
                }
            )
        except Exception:
            att_inputs.append({"name": name, "path": str(p), "sha256": "", "bytes": 0, "rows": 0})

    report: dict[str, Any] = {
        "attestation": {
            "rulepack": {"id": rp_id, "version": rp_ver, "path": str(rp_path)},
            "inputs": att_inputs,
            "timestamp": now_iso,
        },
        # New but non-breaking echo of provided inputs
        "metadata": {"inputs": {k: str(v) for k, v in inputs_map.items()}},
        "summary": {"pass": 0, "warn": 0, "fail": 0},
        "resources": [],
    }

    # ---- Per-resource rules, matched by resource.pattern against file name
    for name, path in inputs_map.items():
        applicable: list[dict[str, Any]] = []
        for res in resources_spec:
            pat = res.get("pattern")
            if pat and _resource_matches(pat, path):
                applicable.extend(res.get("rules", []) or [])

        if not applicable:
            continue

        df = frames[name]
        resource_rules: list[dict[str, Any]] = []

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
                    elif rtype == "foreign_key":
                        # Simple cross-table FK presence check
                        frm = r.get("from", {}) or {}
                        to = r.get("to", {}) or {}
                        status, evidence = _check_foreign_key(
                            frames,
                            from_table=frm.get("table", ""),
                            from_field=frm.get("field", ""),
                            to_table=to.get("table", ""),
                            to_field=to.get("field", ""),
                            severity=severity,
                        )
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
            if status == "FAIL":
                report["summary"]["fail"] += 1
            elif status == "WARN":
                report["summary"]["warn"] += 1
            else:
                report["summary"]["pass"] += 1

        # attach resource block (keep 'path' for MD writer compatibility)
        res_block = {"name": name, "path": str(path), "rules": resource_rules}
        report["resources"].append(res_block)

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


# ---------------- Foreign key (multi-input) ----------------


def _check_foreign_key(
    frames: dict[str, pd.DataFrame],
    from_table: str,
    from_field: str,
    to_table: str,
    to_field: str,
    severity: str,
) -> tuple[str, dict[str, Any]]:
    if not from_table or not to_table or not from_field or not to_field:
        return "FAIL", {"error": "config_missing_fk_fields"}
    if from_table not in frames or to_table not in frames:
        return (
            "FAIL",
            {
                "error": "unknown_table",
                "message": f"Have tables {sorted(frames.keys())}; "
                f"need: {from_table}, {to_table}",
            },
        )

    left = (
        frames[from_table][from_field]
        if from_field in frames[from_table].columns
        else pd.Series(dtype="object")
    )
    right = (
        frames[to_table][to_field]
        if to_field in frames[to_table].columns
        else pd.Series(dtype="object")
    )

    if left.empty and from_field not in frames[from_table].columns:
        return "FAIL", {"error": "column_not_found", "column": f"{from_table}.{from_field}"}
    if right.empty and to_field not in frames[to_table].columns:
        return "FAIL", {"error": "column_not_found", "column": f"{to_table}.{to_field}"}

    missing = sorted(set(left.dropna().unique()) - set(right.dropna().unique()))
    if missing:
        return _status_from_severity(severity), {
            "missing_values": missing[:50],
            "missing_count_estimate": len(missing),
            "from": {"table": from_table, "field": from_field},
            "to": {"table": to_table, "field": to_field},
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
