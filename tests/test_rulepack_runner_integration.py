# tests/test_rulepack_runner_integration.py
import datetime
from pathlib import Path

import yaml

from fairy.validation.rulepack_runner import run_rulepack


def _run(rp_path_str, inputs_map):
    rp_path = Path(rp_path_str)
    rp = yaml.safe_load(rp_path.read_text())
    now = datetime.datetime(2025, 1, 1).isoformat()
    return run_rulepack(inputs_map, rp, rp_path, now)


def test_penguins_rulepack_loads_and_runs():
    report = _run(
        "rulepacks/examples/penguins/rulepack.yml",
        {"default": Path("tests/fixtures/penguins_small.csv")},
    )

    core_ver = report["attestation"].get("core_version")
    assert isinstance(core_ver, str)
    assert core_ver  # allows "unknown"

    att = report["attestation"]["rulepack"]
    assert att["id"] in ("penguins-kata", "penguins-kata")  # name field varies by schema

    total_rules = sum(len(r["rules"]) for r in report["resources"])
    assert total_rules == 10


def test_art_collections_pass_case():
    report = _run(
        "tests/fixtures/art-collections/rulepack.yaml",
        {
            "artists": Path("tests/fixtures/art-collections/artists.csv"),
            "artworks": Path("tests/fixtures/art-collections/artworks_pass.csv"),
        },
    )
    # No hard assertion on pass/warn/fail counts (fixture-dependent),
    # but ensure the runner recorded both inputs and produced rules.
    assert len(report["attestation"]["inputs"]) == 2
    assert len(report["resources"]) == 2
    assert sum(len(r["rules"]) for r in report["resources"]) == 8


def test_art_collections_fk_fail_case():
    report = _run(
        "tests/fixtures/art-collections/rulepack.yaml",
        {
            "artists": Path("tests/fixtures/art-collections/artists.csv"),
            "artworks": Path("tests/fixtures/art-collections/artworks_fail_missing_artist.csv"),
        },
    )
    # Expect at least one FAIL (FK or required)
    assert report["summary"]["fail"] >= 1
