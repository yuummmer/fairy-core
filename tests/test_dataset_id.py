# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2025 Jennifer Slotnick

from hashlib import sha256

from fairy.core.services.provenance import (
    CANON_VERSION_V1,
    compute_dataset_id,
    compute_params_sha256,
)


def _expected_v1(
    *,
    inputs_sha256: dict[str, str],
    rulepack: dict[str, str],
    params_sha256: str,
    canon_version: str = CANON_VERSION_V1,
) -> str:
    # mirror provenance.compute_dataset_id payload exactly
    import json as _json

    payload = {
        "canon_version": canon_version,
        "algorithm": "sha256",
        "includes": ["inputs.sha256", "rulepack.sha256", "params.sha256"],
        "inputs": {k: {"sha256": v} for k, v in sorted(inputs_sha256.items())},
        "rulepack": {
            "id": rulepack["id"],
            "version": rulepack["version"],
            "sha256": rulepack["sha256"],
        },
        "params": {"sha256": params_sha256},
    }
    canon = _json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    h = sha256(canon.encode("utf-8")).hexdigest()
    return f"sha256:{h}"


def test_compute_dataset_id_deterministic():
    inputs_sha256 = {"samples": "a" * 64}
    rulepack = {"id": "RP", "version": "1.0.0", "sha256": "b" * 64}
    params_sha = compute_params_sha256(None)

    r1 = compute_dataset_id(
        inputs_sha256=inputs_sha256,
        rulepack=rulepack,
        params_sha256=params_sha,
        canon_version=CANON_VERSION_V1,
    )
    r2 = compute_dataset_id(
        inputs_sha256=inputs_sha256,
        rulepack=rulepack,
        params_sha256=params_sha,
        canon_version=CANON_VERSION_V1,
    )
    assert r1 == r2
    assert r1.startswith("sha256:")
    assert len(r1) == 7 + 64


def test_compute_dataset_id_matches_expected_payload_hash():
    inputs_sha256 = {"samples": "a" * 64, "files": "c" * 64}
    rulepack = {"id": "RP", "version": "1.0.0", "sha256": "b" * 64}
    params_sha = compute_params_sha256({"x": 1, "y": 2})

    got = compute_dataset_id(
        inputs_sha256=inputs_sha256,
        rulepack=rulepack,
        params_sha256=params_sha,
        canon_version=CANON_VERSION_V1,
    )
    exp = _expected_v1(inputs_sha256=inputs_sha256, rulepack=rulepack, params_sha256=params_sha)
    assert got == exp


def test_compute_dataset_id_changes_if_any_input_sha_changes():
    inputs1 = {"samples": "a" * 64}
    inputs2 = {"samples": "d" * 64}  # one byte different effectively
    rulepack = {"id": "RP", "version": "1.0.0", "sha256": "b" * 64}
    params_sha = compute_params_sha256({})

    r1 = compute_dataset_id(inputs_sha256=inputs1, rulepack=rulepack, params_sha256=params_sha)
    r2 = compute_dataset_id(inputs_sha256=inputs2, rulepack=rulepack, params_sha256=params_sha)
    assert r1 != r2


def test_compute_dataset_id_changes_if_params_change():
    inputs = {"samples": "a" * 64}
    rulepack = {"id": "RP", "version": "1.0.0", "sha256": "b" * 64}
    p1 = compute_params_sha256({"a": 1})
    p2 = compute_params_sha256({"a": 2})

    r1 = compute_dataset_id(inputs_sha256=inputs, rulepack=rulepack, params_sha256=p1)
    r2 = compute_dataset_id(inputs_sha256=inputs, rulepack=rulepack, params_sha256=p2)
    assert r1 != r2


def test_compute_dataset_id_changes_if_rulepack_changes():
    inputs = {"samples": "a" * 64}
    params_sha = compute_params_sha256({})

    rp1 = {"id": "RP", "version": "1.0.0", "sha256": "b" * 64}
    rp2 = {"id": "RP", "version": "1.0.1", "sha256": "b" * 64}

    r1 = compute_dataset_id(inputs_sha256=inputs, rulepack=rp1, params_sha256=params_sha)
    r2 = compute_dataset_id(inputs_sha256=inputs, rulepack=rp2, params_sha256=params_sha)
    assert r1 != r2


def test_compute_dataset_id_changes_if_canon_version_changes():
    inputs = {"samples": "a" * 64}
    rulepack = {"id": "RP", "version": "1.0.0", "sha256": "b" * 64}
    params_sha = compute_params_sha256({})

    r1 = compute_dataset_id(
        inputs_sha256=inputs,
        rulepack=rulepack,
        params_sha256=params_sha,
        canon_version="fairy-canon@1",
    )
    r2 = compute_dataset_id(
        inputs_sha256=inputs,
        rulepack=rulepack,
        params_sha256=params_sha,
        canon_version="fairy-canon@2",
    )
    assert r1 != r2
