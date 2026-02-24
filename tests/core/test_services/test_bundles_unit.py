from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pytest

from fairy.core.services import bundles
from fairy.core.services.bundles import BundleError, BundleFormatSpec, BundleResult


class FakePackager:
    format_id = "fake"
    description = "fake packager for tests"

    def __init__(self, format_id: str = "fake") -> None:
        self.format_id = format_id
        self.calls: list[tuple[bundles.BundleRequest, dict[str, Any]]] = []

    def create_bundle(
        self,
        req: bundles.BundleRequest,
        options: Mapping[str, Any],
    ) -> BundleResult:
        self.calls.append((req, dict(options)))
        return BundleResult(
            bundle_path=req.out_dir / "bundle.fake",
            format_id=self.format_id,
            metadata={"called": True},
        )


def _fresh_registry_with_fake(fake: FakePackager) -> bundles.BundleRegistry:
    reg = bundles.BundleRegistry()
    reg.register(BundleFormatSpec(packager=fake, default_options={"a": 1, "b": 2}))
    return reg


def test_unknown_format_error_message(monkeypatch, tmp_path):
    # isolate global registry
    reg = bundles.BundleRegistry()
    fake = FakePackager()
    reg.register(BundleFormatSpec(packager=fake))
    monkeypatch.setattr(bundles, "BUNDLE_REGISTRY", reg)

    with pytest.raises(BundleError) as excinfo:
        bundles.create_bundle(
            format_id="unknown",
            payload_path=tmp_path / "payload.bin",
            artifacts_dir=tmp_path / "artifacts",
            out_dir=tmp_path / "out",
        )

    msg = str(excinfo.value)
    assert "Unknown bundle format: unknown" in msg
    assert "Available: fake" in msg


def test_option_precedence_and_request_passthrough(monkeypatch, tmp_path):
    fake = FakePackager()
    reg = _fresh_registry_with_fake(fake)
    monkeypatch.setattr(bundles, "BUNDLE_REGISTRY", reg)

    payload_path = tmp_path / "payload.bin"
    artifacts_dir = tmp_path / "artifacts"
    out_dir = tmp_path / "out"

    config_opts = {"b": "config", "c": "config"}
    cli_opts = {"c": "cli", "d": "cli"}

    result = bundles.create_bundle(
        format_id="fake",
        payload_path=payload_path,
        artifacts_dir=artifacts_dir,
        out_dir=out_dir,
        dataset_id="DATASET-123",
        config_options=config_opts,
        cli_options=cli_opts,
    )

    assert fake.calls, "packager was not invoked"
    ((req, opts),) = fake.calls

    # option precedence: defaults < config < cli
    assert opts == {"a": 1, "b": "config", "c": "cli", "d": "cli"}

    # request fields are passed through as-is
    assert req.payload_path == payload_path
    assert req.artifacts_dir == artifacts_dir
    assert req.out_dir == out_dir
    assert req.dataset_id == "DATASET-123"

    # sanity check on result passthrough
    assert result.bundle_path == out_dir / "bundle.fake"
    assert result.format_id == "fake"
    assert result.metadata.get("called") is True


def test_register_duplicate_format_id_raises():
    reg = bundles.BundleRegistry()
    fake1 = FakePackager()
    fake2 = FakePackager()

    reg.register(BundleFormatSpec(packager=fake1))

    with pytest.raises(BundleError) as excinfo:
        reg.register(BundleFormatSpec(packager=fake2))

    assert "Duplicate bundle format: fake" in str(excinfo.value)


def test_list_format_ids_and_formats_are_sorted_and_stable():
    reg = bundles.BundleRegistry()
    # register in non-sorted order
    reg.register(BundleFormatSpec(packager=FakePackager("z-format"), description="Z desc"))
    reg.register(BundleFormatSpec(packager=FakePackager("a-format"), description="A desc"))
    reg.register(BundleFormatSpec(packager=FakePackager("m-format"), description="M desc"))

    ids = reg.list_format_ids()
    assert ids == ["a-format", "m-format", "z-format"]

    formats = reg.list_formats()
    # list_formats should follow the same sorted order
    assert [fmt for fmt, _ in formats] == ["a-format", "m-format", "z-format"]
    # and descriptions should match their specs
    assert formats == [
        ("a-format", "A desc"),
        ("m-format", "M desc"),
        ("z-format", "Z desc"),
    ]
