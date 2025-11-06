import re
from typing import List, Dict, Set
import pandas as pd

from ..validation_api import Meta, WarningItem, register


class RNAValidator:
    name = "rna"
    version = "0.1.0"

    REQUIRED = ["sample_id"]
    OPTIONAL = ["collection_date", "tissue", "cell_line", "cell_type", "read_length"]

    def validate(self, path: str) -> Meta:
        df = pd.read_csv(path)

        warnings: List[WarningItem] = []
        warnings.extend(check_required_columns(df, self.REQUIRED))
        warnings.extend(check_not_null(df, "sample_id"))
        warnings.extend(check_read_length(df, "read_length"))
        # we could also run check_dates_iso8601 here, etc.

        fields = [c for c in df.columns if c in set(self.REQUIRED + self.OPTIONAL)]

        return Meta(
            n_rows=int(df.shape[0]),
            n_cols=int(df.shape[1]),
            fields_validated=sorted(fields),
            warnings=warnings[:200],
        )


register("rna", RNAValidator())


#
# === helpers used by 'validate' and 'preflight'
#

def check_required_columns(df: pd.DataFrame, required_cols: List[str]) -> List[WarningItem]:
    """
    Spec: rule['check']['type'] == 'require_columns'
          rule['check']['required_columns'] = [...]
    We FAIL (severity="error") if any required col is missing.
    """
    issues: List[WarningItem] = []
    for col in required_cols:
        if col not in df.columns:
            issues.append(
                WarningItem(
                    column=col,
                    kind="missing_column",
                    message=f"Required column '{col}' is missing.",
                    severity="error",
                    row=None,
                    hint="Add this column before submission.",
                )
            )
    return issues


def check_not_null(df: pd.DataFrame, col: str) -> List[WarningItem]:
    """
    Used in simple CSV validation, not directly by run_rulepack().
    FAIL (severity='error') if a required field is blank/null.
    """
    issues: List[WarningItem] = []
    if col in df.columns:
        nullish = df[col].isna() | df[col].astype(str).str.strip().eq("")
        for r in df.index[nullish]:
            issues.append(
                WarningItem(
                    column=col,
                    kind="missing_value",
                    message=f"Missing value in required field '{col}'.",
                    severity="error",
                    row=int(r),
                    hint="Fill this cell.",
                )
            )
    return issues


def check_read_length(df: pd.DataFrame, col: str) -> List[WarningItem]:
    """
    Just an example QC: read_length should be numeric >= 1.
    We'll WARN (severity='warning') if not.
    """
    issues: List[WarningItem] = []
    if col in df.columns:
        rl = pd.to_numeric(df[col], errors="coerce").fillna(-1)
        bad_mask = rl < 1
        for r in df.index[bad_mask]:
            issues.append(
                WarningItem(
                    column=col,
                    kind="invalid_read_length",
                    message="read_length must be >= 1",
                    severity="warning",
                    row=int(r),
                    hint="Use an integer read length like 50, 75, 100...",
                )
            )
    return issues


#
# === helpers only used by run_rulepack() / rulepack-driven checks
#

def check_bio_context(df: pd.DataFrame, biological_context_cols: List[str]) -> List[WarningItem]:
    """
    Spec: type == 'at_least_one_nonempty_per_row'
          spec['column_groups'][0] = ["tissue", "cell_line", "cell_type", ...]
    For each row in samples, at least ONE of those columns must be non-empty.
    If no biological context at all => FAIL (severity='error').
    """
    issues: List[WarningItem] = []

    for idx, row in df.iterrows():
        has_any = False
        for col in biological_context_cols:
            if col in df.columns:
                val = str(row.get(col, "")).strip()
                if val != "":
                    has_any = True
                    break

        if not has_any:
            sid = row.get("sample_id", f"row_{idx}")
            issues.append(
                WarningItem(
                    column=None,
                    kind="bio_context_missing",
                    message=f"Sample '{sid}' does not provide tissue/cell_line/cell_type.",
                    severity="error",
                    row=int(idx),
                    hint="Fill at least one of: tissue, cell_line, or cell_type.",
                )
            )

    return issues


def check_id_crossmatch(
    samples_df: pd.DataFrame,
    files_df: pd.DataFrame,
    *,
    samples_key: str,
) -> List[WarningItem]:
    """
    Spec: type == 'id_crosscheck'
          spec['left_key'] -> passed in as samples_key

    We enforce: every files_df[samples_key] must exist in samples_df[samples_key].
    Missing or unknown sample_id => FAIL (severity='error').
    """
    issues: List[WarningItem] = []

    # If the expected column doesn't exist in either frame, just bail cleanly
    if samples_key not in samples_df.columns or samples_key not in files_df.columns:
        return issues

    # Build known IDs from samples.tsv
    known_ids: Set[str] = set(
        str(x).strip()
        for x in samples_df[samples_key].fillna("")
        if str(x).strip() != ""
    )

    # Check each row in files.tsv
    for idx, row in files_df.iterrows():
        sid = str(row.get(samples_key, "")).strip()
        if sid == "":
            issues.append(
                WarningItem(
                    column=samples_key,
                    kind="file_missing_sample_id",
                    message="Row in files.tsv has no sample_id.",
                    severity="error",
                    row=int(idx),
                    hint="Each file row must name the sample_id it belongs to.",
                )
            )
        elif sid not in known_ids:
            issues.append(
                WarningItem(
                    column=samples_key,
                    kind="file_unknown_sample_id",
                    message=f"File references sample_id '{sid}' not found in samples.tsv.",
                    severity="error",
                    row=int(idx),
                    hint="Fix sample_id or add that sample to samples.tsv.",
                )
            )

    return issues


def check_paired_end_complete(
    files_df: pd.DataFrame,
    *,
    samples_key: str,
    layout_col: str,
    paired_value: str,
    file_col: str,
    r1_pattern: str,
    r2_pattern: str,
) -> List[WarningItem]:
    """
    Spec: type == 'paired_end_complete'
          spec provides:
            samples_key                e.g. "sample_id"
            layout_column              e.g. "layout"
            layout_value_for_paired    e.g. "PAIRED"
            file_column                e.g. "filename"
            r1_pattern                 e.g. "_R1"
            r2_pattern                 e.g. "_R2"

    Rule: for each paired sample (layout == paired_value),
    we expect both an R1 and an R2 file for that sample.
    Missing mate => FAIL.
    """
    issues: List[WarningItem] = []

    rx_r1 = re.compile(r1_pattern)
    rx_r2 = re.compile(r2_pattern)

    # Filter just the paired rows first
    paired_rows = files_df[
        (files_df.get(layout_col, "").astype(str).str.upper() == paired_value.upper())
    ]

    # Group by sample id
    for sid, group in paired_rows.groupby(samples_key):
        if file_col not in group.columns:
            continue

        filenames = group[file_col].astype(str).tolist()

        has_r1 = any(rx_r1.search(fn) for fn in filenames)
        has_r2 = any(rx_r2.search(fn) for fn in filenames)

        if not has_r1 or not has_r2:
            first_idx = int(group.index[0]) if len(group.index) > 0 else None
            issues.append(
                WarningItem(
                    column=file_col,
                    kind="paired_end_incomplete",
                    message=f"Paired-end sample '{sid}' is missing R1 or R2 FASTQ.",
                    severity="error",
                    row=first_idx,
                    hint="Provide both *_R1* and *_R2* files for each paired-end sample.",
                )
            )

    return issues


def check_dates_iso8601(
    df: pd.DataFrame,
    date_cols: List[str],
) -> List[WarningItem]:
    """
    Spec: type == 'dates_are_iso8601'
          spec['columns'] = ["collection_date", ...]

    Rule: each non-empty value in those columns must match YYYY-MM-DD.
    Violations are WARN, not FAIL.
    """
    issues: List[WarningItem] = []
    iso_pat = re.compile(r"^\d{4}-\d{2}-\d{2}$")

    for col in date_cols:
        if col not in df.columns:
            continue
        for idx, raw in df[col].items():
            val = str(raw).strip()
            if val == "":
                continue
            if not iso_pat.match(val):
                issues.append(
                    WarningItem(
                        column=col,
                        kind="invalid_iso8601_date",
                        message=f"Value '{val}' in {col} is not ISO8601 (YYYY-MM-DD).",
                        severity="warning",
                        row=int(idx),
                        hint="Use format YYYY-MM-DD, e.g. 2025-10-02.",
                    )
                )
    return issues


def check_processed_data_present(
    files_df: pd.DataFrame,
    *,
    samples_key: str,
    raw_file_glob: str,
    processed_globs: List[str],
) -> List[WarningItem]:
    """
    Spec: type == 'processed_data_present'
          spec['samples_key']                e.g. "sample_id"
          spec['raw_file_glob']              e.g. ".fastq"
          spec['processed_glob_candidates']  e.g. [".counts.", ".quant."]

    Rule: for each sample, if we see raw FASTQs, do we also see at least
    one processed/quant file? If not, WARN.
    """
    issues: List[WarningItem] = []

    if samples_key not in files_df.columns:
        return issues

    def is_raw(fn: str) -> bool:
        return raw_file_glob in fn

    def is_processed(fn: str) -> bool:
        return any(pat in fn for pat in processed_globs)

    for sid, group in files_df.groupby(samples_key):
        fns = group["filename"].astype(str).tolist() if "filename" in group.columns else []

        has_raw = any(is_raw(fn) for fn in fns)
        has_proc = any(is_processed(fn) for fn in fns)

        if has_raw and not has_proc:
            first_idx = int(group.index[0]) if len(group.index) > 0 else None
            issues.append(
                WarningItem(
                    column="filename",
                    kind="no_processed_files",
                    message=f"Sample '{sid}' has raw data but no processed/quant files.",
                    severity="warning",
                    row=first_idx,
                    hint="Include at least one processed output (e.g. counts matrix).",
                )
            )

    return issues
