import json
from pathlib import Path
from types import SimpleNamespace

import jsonschema
from jsonschema import Draft202012Validator

from fairy.cli import cmd_preflight


def test_preflight_emits_manifest_v1_and_links_to_report(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]

    rulepack_path = repo_root / "tests" / "fixtures" / "rulepacks" / "geo_bulk_seq_min_v0_2_0.json"
    samples_path = repo_root / "tests" / "fixtures" / "geo_bulk_seq_min" / "samples.tsv"
    files_path = repo_root / "tests" / "fixtures" / "geo_bulk_seq_min" / "files.tsv"

    assert rulepack_path.exists()
    assert samples_path.exists()
    assert files_path.exists()

    out_path = tmp_path / "geo_bulk_seq_report.json"

    args = SimpleNamespace(
        rulepack=rulepack_path,
        samples=samples_path,
        files=files_path,
        out=out_path,
        fairy_version="0.2.2",
        param_file=None,
    )

    # --- Act ---
    rc = cmd_preflight.main(args)
    assert rc == 0

    # --- Assert: artifacts exist ---
    assert out_path.exists()
    md_path = out_path.with_suffix(".md")
    assert md_path.exists()
    manifest_path = out_path.parent / "manifest.json"
    assert manifest_path.exists()

    report = json.loads(out_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    # --- Assert: schema-valid manifest ---
    schema_path = repo_root / "schemas" / "manifest_v1.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))

    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema, format_checker=jsonschema.FormatChecker())
    errors = sorted(validator.iter_errors(manifest), key=lambda e: e.path)
    assert errors == [], "Schema validation failed:\n" + "\n".join(
        f"- {list(e.path)}: {e.message}" for e in errors
    )

    # --- Assert: linkage to report is correct/deterministic ---
    assert manifest["source_report"] == out_path.name
    assert manifest["dataset_id"] == report["dataset_id"]
    assert manifest["created_at_utc"] == report["generated_at"]

    expected_fairy_version = (report.get("engine") or {}).get(
        "fairy_core_version"
    ) or args.fairy_version
    assert manifest["fairy_version"] == expected_fairy_version

    assert manifest["rulepack"]["id"] == report["metadata"]["rulepack"]["id"]
    assert manifest["rulepack"]["version"] == report["metadata"]["rulepack"]["version"]

    # --- Assert: all file entries have roles + expected report roles exist ---
    assert all("role" in f and f["role"] for f in manifest["files"])

    paths_to_roles = {f["path"]: f["role"] for f in manifest["files"]}
    assert paths_to_roles[out_path.name] == "report"
    assert paths_to_roles[md_path.name] == "report"
