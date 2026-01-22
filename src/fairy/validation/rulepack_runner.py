# src/fairy/validate/rulepack_runner.py
from __future__ import annotations

import importlib.metadata as md
import re
from fnmatch import fnmatch
from hashlib import sha256
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import pandas as pd

# Accept both names for the row-duplicates rule (+ foreign_key for multi-input)
CHECK_TYPES = {
    "dup",
    "unique",
    "enum",
    "range",
    "no_duplicate_rows",
    "foreign_key",
    "required",
    "url",
    "non_empty_trimmed",
    "regex",
}

MAX_REMEDIATION_LINKS = 20

# URI scheme-ish validation for url checks
_SCHEME_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*$")


def _extract_meta(rulepack: dict) -> tuple[str, str]:
    # New schema (id/version at top-level)
    if isinstance(rulepack, dict) and ("id" in rulepack or "version" in rulepack):
        return rulepack.get("id", "") or "", rulepack.get("version", "") or ""
    # Old schema (meta.name/meta.version)
    meta = rulepack.get("meta", {}) if isinstance(rulepack, dict) else {}
    rid = meta.get("name") or meta.get("id") or ""
    rver = meta.get("version") or ""
    return rid, rver


def _normalize_old_rule(rule: dict) -> dict:
    """Flatten old-schema rule so access is uniform (id/type/severity + params + _pattern)."""
    cfg = rule.get("config", {}) or {}
    out = {
        "id": rule.get("id", "") or "",
        "type": (rule.get("type", "") or "").strip(),
        "severity": (rule.get("severity", "fail") or "fail").lower(),
        "_pattern": cfg.get("pattern", "") or "",
    }
    for k, v in cfg.items():
        if k != "pattern":
            out[k] = v
    return out


def _old_schema_applicable_rules(rules: list[dict], path: Path) -> list[dict]:
    name = path.name
    acc: list[dict] = []
    for r in rules or []:
        rr = _normalize_old_rule(r)
        pat = rr.get("_pattern", "")
        if not pat:
            continue
        if ("*" in pat and fnmatch(name, pat)) or (name == pat):
            acc.append(rr)
    return acc


def _sha256(path: Path) -> str:
    h = sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _resource_matches(pattern: str, path: Path) -> bool:
    if not pattern:
        return False
    return fnmatch(path.name, pattern)


def _infer_sep(path: Path) -> str:
    suf = path.suffix.lower()
    if suf in {".tsv", ".tab"}:
        return "\t"
    return ","


def _read_table(path: Path, delimiter: str | None = None) -> pd.DataFrame:
    sep = delimiter if delimiter is not None else _infer_sep(path)
    return pd.read_csv(
        path,
        sep=sep,
        dtype=str,
        keep_default_na=False,  # keep empty strings as ""
    )


def run_rulepack(
    inputs_map: dict[str, Path],
    rulepack: dict,
    rp_path: Path,
    now_iso: str,
    *,
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Validate one or more inputs using a rulepack.

    inputs_map: name -> CSV Path
      - legacy single-file mode: {"default": <file>}
      - folder/explicit multi:   {"artworks": <path>, "artists": <path>, ...}
    """
    # ---- Read meta from either schema
    rp_id, rp_ver = _extract_meta(rulepack)

    # Schema branches (new vs old)
    new_resources = (rulepack.get("resources") or []) if isinstance(rulepack, dict) else []
    old_rules = (rulepack.get("rules") or []) if isinstance(rulepack, dict) else []

    # ---- Load all inputs once (enables cross-table checks)
    frames: dict[str, pd.DataFrame] = {}
    for name, path in inputs_map.items():
        frames[name] = _read_table(path)  # delimiter override later via CLI threading

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

    try:
        core_version = md.version("fairy-core")
    except md.PackageNotFoundError:
        core_version = "unknown"

    rulepack_obj = {"id": rp_id, "version": rp_ver, "path": str(rp_path)}

    report: dict[str, Any] = {
        "engine": {"fairy_core_version": core_version},
        "attestation": {
            "core_version": core_version,
            "rulepack": rulepack_obj,
            "inputs": att_inputs,
            "timestamp": now_iso,
            "fairy_core_version": core_version,
            "rulepack_name": rp_id or "UNKNOWN_RULEPACK",
            "rulepack_version": rp_ver or "0.0.0",
            "rulepack_source_path": str(rp_path),
        },
        # New but non-breaking echo of provided inputs
        "metadata": {"inputs": {k: str(v) for k, v in inputs_map.items()}},
        "summary": {"pass": 0, "warn": 0, "fail": 0},
        "resources": [],
    }

    # ---- Per-resource rules (match by pattern against filename)
    for name, path in inputs_map.items():
        applicable: list[dict[str, Any]] = []

        if new_resources:
            for res in new_resources:
                pat = res.get("pattern")
                if pat and _resource_matches(pat, path):
                    applicable.extend(res.get("rules", []) or [])
        elif old_rules:
            applicable.extend(_old_schema_applicable_rules(old_rules, path))

        df = frames[name]
        resource_rules: list[dict[str, Any]] = []

        for r in sorted(applicable, key=lambda x: x.get("id", "")):
            rule_id = r.get("id", "")
            rtype = (r.get("type", "") or "").strip()
            severity = (r.get("severity", "fail") or "fail").lower()
            status = "PASS"
            evidence: dict[str, Any] = {}
            rem_col = r.get("remediation_link_column")
            rem_label = r.get("remediation_link_label")

            if rtype not in CHECK_TYPES:
                status, evidence = "FAIL", {
                    "error": "unknown_rule_type",
                    "type": rtype,
                    "message": (
                        f"Unknown rule type '{rtype}'. "
                        "This rulepack may require a newer version of fairy-core. "
                        "Please upgrade fairy-core and re-run."
                    ),
                    "supported_types": sorted(CHECK_TYPES),
                }
            else:
                try:
                    if rtype in ("dup", "no_duplicate_rows"):
                        keys = r.get("keys", [])
                        status, evidence = check_dup(df, keys, severity, rem_col, rem_label)

                    elif rtype == "unique":
                        cols = r.get("columns", [])
                        status, evidence = check_unique(df, cols, severity, rem_col, rem_label)

                    elif rtype == "enum":
                        col = r.get("column")
                        allow = r.get("allow", [])
                        normalize = r.get("normalize", {}) or {}
                        status, evidence = check_enum(
                            df, col, allow, normalize, severity, rem_col, rem_label
                        )

                    elif rtype == "range":
                        col = r.get("column")
                        mn = r.get("min", None)
                        mx = r.get("max", None)
                        inclusive = bool(r.get("inclusive", True))
                        status, evidence = check_range(
                            df, col, mn, mx, inclusive, severity, rem_col, rem_label
                        )

                    elif rtype == "foreign_key":
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

                    elif rtype == "required":
                        cols = r.get("columns", []) or r.get("cols", [])
                        status, evidence = check_required(df, cols, severity, rem_col, rem_label)

                    elif rtype == "url":
                        col = r.get("column")
                        schemes = r.get("schemes") or r.get("scheme")
                        status, evidence = check_url(df, col, schemes, severity, rem_col, rem_label)

                    elif rtype == "non_empty_trimmed":
                        col = r.get("column")
                        status, evidence = check_non_empty_trimmed(
                            df, col, severity, rem_col, rem_label
                        )
                    elif rtype == "regex":
                        col = r.get("column")
                        regex_pattern = r.get("regex")
                        mode = (r.get("mode") or "not_matches").strip()
                        ignore_empty = bool(r.get("ignore_empty", True))

                        status, evidence = check_regex(
                            df,
                            column=col,
                            regex=regex_pattern,
                            mode=mode,
                            ignore_empty=ignore_empty,
                            severity=severity,
                            rem_col=rem_col,
                            rem_label=rem_label,
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

        # Always append a resource block for this input (even if no rules matched)
        res_block = {"name": name, "path": str(path), "rules": resource_rules}
        report["resources"].append(res_block)

    return report


# ---------------- Checks (1-based row indices) ----------------


def _rows_1based(rows0: list[int]) -> list[int]:
    return [int(i) + 1 for i in rows0]


def _status_from_severity(sev: str) -> str:
    return "FAIL" if (sev or "fail") == "fail" else "WARN"


def _href(url: str) -> str:
    """Make URLs clickable in Markdown/HTML without mutating stored raw data."""
    u = (url or "").strip()
    if not u:
        return u
    if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", u):
        return u  # already has a scheme like http:, https:, mailto:
    return f"https://{u}"


def _collect_remediation_links(
    df: pd.DataFrame,
    rows_1based: list[int],
    remediation_col: str | None,
    remediation_label: str | None,
) -> dict[str, Any] | None:
    if not remediation_col:
        return None
    if remediation_col not in df.columns:
        return None

    links: list[dict[str, Any]] = []
    for r1 in rows_1based:
        r0 = int(r1) - 1
        if r0 < 0 or r0 >= len(df):
            continue
        raw = df.iloc[r0][remediation_col]
        if pd.isna(raw):
            continue
        url = str(raw).strip()
        if not url:
            continue
        links.append({"row": int(r1), "url": url})

    if not links:
        return None

    out: dict[str, Any] = {"column": remediation_col, "links": links}
    if remediation_label:
        out["label"] = remediation_label
    return out


def check_dup(
    df: pd.DataFrame,
    keys: list[str],
    severity: str,
    rem_col=None,
    rem_label=None,
) -> tuple[str, dict[str, Any]]:
    if not keys:
        return "FAIL", {"error": "config_missing_keys"}
    for k in keys:
        if k not in df.columns:
            return "FAIL", {"error": "column_not_found", "column": k}

    dup_mask = df.duplicated(subset=keys, keep="first")
    dup_pos = dup_mask.to_numpy().nonzero()[0].tolist()

    if dup_pos:
        rows = _rows_sorted_1based(dup_pos)

        ev = {
            "duplicates": [{"rows": rows}],
            "count": len(rows),
        }

        rem = _collect_remediation_links(df, rows, rem_col, rem_label)
        if rem:
            ev["remediation"] = rem

        return _status_from_severity(severity), ev

    return "PASS", {"count": 0}


def check_unique(
    df: pd.DataFrame, columns: list[str], severity: str, rem_col=None, rem_label=None
) -> tuple[str, dict[str, Any]]:
    if not columns:
        return "FAIL", {"error": "config_missing_columns"}
    for c in columns:
        if c not in df.columns:
            return "FAIL", {"error": "column_not_found", "column": c}

    # composite unique via tuple
    series = df[columns].astype(object).apply(tuple, axis=1)
    dup_mask = series.duplicated(keep="first")

    dup_pos = dup_mask.to_numpy().nonzero()[0].tolist()

    if dup_pos:
        rows = _rows_sorted_1based(dup_pos)

        ev = {
            "duplicates": [{"rows": rows}],
            "count": len(rows),
        }

        rem = _collect_remediation_links(df, rows, rem_col, rem_label)
        if rem:
            ev["remediation"] = rem

        return _status_from_severity(severity), ev

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
    df: pd.DataFrame,
    column: str,
    allow: list[Any],
    normalize: dict[str, Any],
    severity: str,
    rem_col=None,
    rem_label=None,
) -> tuple[str, dict[str, Any]]:
    if not column:
        return "FAIL", {"error": "config_missing_column"}
    if column not in df.columns:
        return "FAIL", {"error": "column_not_found", "column": column}
    if not isinstance(allow, list) or not allow:
        return "FAIL", {"error": "config_missing_allow"}

    # normalize allow list if requested
    norm_allow = [_normalize(a, normalize) for a in allow] if normalize else allow

    out: list[int] = []
    for i, v in enumerate(df[column].tolist()):
        vv = _normalize(v, normalize or {})
        if pd.isna(vv) or vv not in norm_allow:
            out.append(i)

    if out:
        rows = _rows_1based(out)

        ev = {"out_of_set": {"count": len(out), "rows": rows}}

        rem = _collect_remediation_links(df, rows, rem_col, rem_label)
        if rem:
            ev["remediation"] = rem

        return _status_from_severity(severity), ev

    return "PASS", {"normalized": bool(normalize)}


def check_range(
    df: pd.DataFrame,
    column: str,
    mn,
    mx,
    inclusive: bool,
    severity: str,
    rem_col=None,
    rem_label=None,
) -> tuple[str, dict[str, Any]]:
    if not column:
        return "FAIL", {"error": "config_missing_column"}
    if column not in df.columns:
        return "FAIL", {"error": "column_not_found", "column": column}

    # numeric-only MVP; datetime can be added later
    series = pd.to_numeric(df[column], errors="coerce")

    out: list[int] = []
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
        rows = _rows_1based(out)

        ev = {"out_of_bounds": {"count": len(out), "rows": rows}}

        rem = _collect_remediation_links(df, rows, rem_col, rem_label)
        if rem:
            ev["remediation"] = rem

        return _status_from_severity(severity), ev

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
                "message": f"Have tables {sorted(frames.keys())}; need: {from_table}, {to_table}",
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


def _rows_sorted_1based(idx_like) -> list[int]:
    return [int(i) + 1 for i in sorted(map(int, idx_like))]


def check_required(
    df: pd.DataFrame, columns: list[str], severity: str, rem_col=None, rem_label=None
) -> tuple[str, dict[str, Any]]:
    if not columns:
        return "FAIL", {"error": "config_missing_columns"}
    missing_cols = [c for c in columns if c not in df.columns]
    ev: dict[str, Any] = {}
    if missing_cols:
        ev["missing_columns"] = sorted(missing_cols)

    present = [c for c in columns if c in df.columns]
    nullish_rows: dict[str, list[int]] = {}
    for c in present:
        # empty after trim OR NaN
        s = df[c]
        mask = s.isna() | s.astype(str).str.strip().eq("")
        if mask.any():
            bad_pos = mask.to_numpy().nonzero()[0].tolist()
            nullish_rows[c] = _rows_sorted_1based(bad_pos)

    if nullish_rows:
        ev["nullish"] = {
            "columns": sorted(nullish_rows.keys()),
            "rows_by_column": {k: v for k, v in sorted(nullish_rows.items())},
        }
        # Count of cells flagged (flat cell count)
        # Row-level counts are fine too; cell count is more informative here.
        ev["count"] = int(sum(len(v) for v in nullish_rows.values()))
        failing_rows = sorted({r for rows in nullish_rows.values() for r in rows})
        rem = _collect_remediation_links(df, failing_rows, rem_col, rem_label)
        if rem:
            ev["remediation"] = rem

    if ev:
        return _status_from_severity(severity), ev
    return "PASS", {"count": 0}


def _url_syntax_ok(val: Any, schemes: set[str]) -> bool:
    if pd.isna(val):
        return True

    try:
        s = str(val).strip()
    except Exception:
        return False

    if s.lower().startswith("www."):
        s = "https://" + s

    parts = urlsplit(s)
    scheme = (parts.scheme or "").lower()

    if not scheme or not _SCHEME_RE.match(scheme):
        return False

    if schemes and scheme not in {x.lower() for x in schemes}:
        return False

    return bool(parts.netloc or parts.path)


def check_url(
    df: pd.DataFrame,
    column: str,
    schemes: list[str] | None,
    severity: str,
    rem_col=None,
    rem_label=None,
) -> tuple[str, dict[str, Any]]:
    if not column:
        return "FAIL", {"error": "config_missing_column"}
    if column not in df.columns:
        return "FAIL", {"error": "column_not_found", "column": column}

    allow = set(schemes or ["http", "https"])
    s = df[column]
    bad_mask = ~s.apply(lambda v: _url_syntax_ok(v, allow))

    if bad_mask.any():
        bad_pos = bad_mask.to_numpy().nonzero()[0].tolist()
        rows = _rows_sorted_1based(bad_pos)

        ev = {
            "invalid_url_rows": rows,
            "count": len(rows),
            "schemes": sorted(allow),
        }

        rem = _collect_remediation_links(df, rows, rem_col, rem_label)
        if rem:
            ev["remediation"] = rem

        return _status_from_severity(severity), ev

    return "PASS", {"count": 0}


def check_non_empty_trimmed(
    df: pd.DataFrame, column: str, severity: str, rem_col=None, rem_label=None
) -> tuple[str, dict[str, Any]]:
    if not column:
        return "FAIL", {"error": "config_missing_column"}
    if column not in df.columns:
        return "FAIL", {"error": "column_not_found", "column": column}

    s = df[column].astype("string")
    bad_mask = s.isna() | (s.str.strip().str.len() == 0)

    if bad_mask.any():
        bad_pos = bad_mask.to_numpy().nonzero()[0].tolist()
        rows = _rows_sorted_1based(bad_pos)

        ev = {
            "empty_or_whitespace_rows": rows,
            "count": len(rows),
        }

        rem = _collect_remediation_links(df, rows, rem_col, rem_label)
        if rem:
            ev["remediation"] = rem

        return _status_from_severity(severity), ev

    return "PASS", {"count": 0}


def check_regex(
    df: pd.DataFrame,
    column: str,
    regex: str,
    mode: str = "not_matches",
    ignore_empty: bool = True,
    severity: str = "fail",
    rem_col=None,
    rem_label=None,
) -> tuple[str, dict[str, Any]]:
    """
    mode:
    - "not_matches": flag non-empty values that do NOT fullmatch (regex)
    - "matches": flag non-empty values that DO search (regex) (forbidden pattern)
    ignore_empty:
    - True: skip NA/empty/whitespace-only values
    - False: evaluate empties too (so "" will fail "not_matches", and will not fail "matches)
    """
    if not column:
        return "FAIL", {"error": "config_missing_column"}
    if column not in df.columns:
        return "FAIL", {"error": "column_not_found", "column": column}
    if not regex:
        return "FAIL", {"error": "config_missing_regex"}

    mode = (mode or "not_matches").strip()
    if mode not in ("not_matches", "matches"):
        return "FAIL", {"error": "config_invalid_mode", "mode": mode}

    rx = None
    try:
        rx = re.compile(regex)
    except (re.error, TypeError) as e:
        return "FAIL", {"error": "invalid_regex", "message": str(e), "regex": regex}

    s = df[column]
    bad_pos: list[int] = []
    ignored_empty_count = 0
    samples: list[dict[str, Any]] = []

    for i, v in enumerate(s.tolist()):
        if pd.isna(v):
            if ignore_empty:
                ignored_empty_count += 1
                continue
            text = ""
        else:
            text = str(v)

        if text.strip() == "":
            if ignore_empty:
                ignored_empty_count += 1
                continue

        violated = False
        if mode == "not_matches":
            # "must match format" => full string match
            violated = rx.fullmatch(text) is None
        else:  # mode == "matches"
            # "forbidden text present" => search anywhere
            violated = rx.search(text) is not None

        if violated:
            bad_pos.append(i)
            if len(samples) < 10:
                samples.append({"row": int(i) + 1, "value": text})

    if bad_pos:
        rows = _rows_sorted_1based(bad_pos)
        ev: dict[str, Any] = {
            "column": column,
            "regex": regex,
            "mode": mode,
            "ignore_empty": bool(ignore_empty),
            "count": len(rows),
            "rows": rows,
        }

        if ignored_empty_count:
            ev["ignored_empty_count"] = int(ignored_empty_count)
        if samples:
            ev["samples"] = samples

        rem = _collect_remediation_links(df, rows, rem_col, rem_label)
        if rem:
            ev["remediation"] = rem

        return _status_from_severity(severity), ev
    # PASS: still return useful meta for debugging
    return "PASS", {
        "column": column,
        "regex": regex,
        "mode": mode,
        "ignore_empty": bool(ignore_empty),
        "count": 0,
    }


# ---------------- Markdown writer (deterministic order) ----------------


def write_markdown(report: dict[str, Any]) -> str:
    eng = report.get("engine", {}) or {}
    att = report.get("attestation", {})
    rp = att.get("rulepack", {})
    ts = att.get("timestamp", "")

    fairy_core_version = (
        eng.get("fairy_core_version")
        or att.get("fairy_core_version")
        or att.get("core_version")
        or ""
    )
    rulepack_name = att.get("rulepack_name") or rp.get("id", "")
    rulepack_version = att.get("rulepack_version") or rp.get("version", "")
    rulepack_source_path = att.get("rulepack_source_path") or rp.get("path", "")

    out: list[str] = []
    out += [
        "# FAIRy Validate Report",
        "",
        f"**Timestamp:** {ts}",
        f"**FAIRy core:** {fairy_core_version}",
        f"**Rulepack:** {rulepack_name}@{rulepack_version}",
        f"**Rulepack source:** {rulepack_source_path}",
        "",
        "## Summary",
        f"- PASS: {report.get('summary', {}).get('pass', 0)}",
        f"- WARN: {report.get('summary', {}).get('warn', 0)}",
        f"- FAIL: {report.get('summary', {}).get('fail', 0)}",
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
        out.append(f"## Findings for `{res.get('path', '')}`")
        for rr in sorted(res.get("rules", []), key=lambda r: r.get("id", "")):
            out.append(f"### [{rr.get('status')}] {rr.get('id')} — {rr.get('type')}")
            ev = rr.get("evidence", {})

            rem = ev.get("remediation")
            if rem and rem.get("links"):
                label = rem.get("label") or "Open record"

                max_links = MAX_REMEDIATION_LINKS
                shown = rem["links"][:max_links]

                out.append("Remediation:")
                for link in shown:
                    out.append(f"- Row {link['row']}: [{label}]({_href(link['url'])})")

                if len(rem["links"]) > max_links:
                    out.append(
                        f"_Showing first {max_links} remediation links (of {len(rem['links'])})._"
                    )

                out.append("")

            if "duplicates" in ev:
                for d in ev["duplicates"]:
                    out.append(f"Duplicates at rows {d.get('rows', [])}")
            if "out_of_set" in ev:
                o = ev["out_of_set"]
                out.append(f"Out of set rows {o.get('rows', [])} (count={o.get('count', 0)})")
            if "out_of_bounds" in ev:
                o = ev["out_of_bounds"]
                out.append(f"Out of bounds rows {o.get('rows', [])} (count={o.get('count', 0)})")
            if ev.get("normalized") is True:
                out.append("Normalized comparison applied.")
            if "error" in ev:
                out.append(f"Error: {ev['error']}")
            if ev.get("regex") and ev.get("rows"):
                out.append(
                    f"Regex {ev.get('mode')} rows {ev.get('rows', [])} (count={ev.get('count', 0)})"
                )
                if ev.get("samples"):
                    for s in ev["samples"][:5]:
                        out.append(f"- Row {s.get('row')}: {s.get('value')}")
        out.append("")
    return "\n".join(out)
