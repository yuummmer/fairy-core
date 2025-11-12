# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2025 Jennifer Slotnick

from hashlib import sha256

import pytest

from fairy.core.services.provenance import compute_dataset_id


def test_compute_dataset_id_single_input():
    """Test dataset_id computation with a single input."""
    inputs_meta = {
        "samples": {
            "sha256": "a" * 64,
            "n_rows": 10,
            "n_cols": 5,
        }
    }

    result = compute_dataset_id(inputs_meta)

    # Verify format
    assert result.startswith("sha256:")
    assert len(result) == 7 + 64  # "sha256:" + 64 hex chars

    # Verify deterministic: same input produces same hash
    result2 = compute_dataset_id(inputs_meta)
    assert result == result2


def test_compute_dataset_id_multiple_inputs_deterministic_ordering():
    """Test that multiple inputs produce deterministic hash regardless of input order."""
    inputs_meta1 = {
        "files": {
            "sha256": "b" * 64,
            "n_rows": 3,
            "n_cols": 3,
        },
        "samples": {
            "sha256": "a" * 64,
            "n_rows": 10,
            "n_cols": 5,
        },
    }

    # Same inputs in different order
    inputs_meta2 = {
        "samples": {
            "sha256": "a" * 64,
            "n_rows": 10,
            "n_cols": 5,
        },
        "files": {
            "sha256": "b" * 64,
            "n_rows": 3,
            "n_cols": 3,
        },
    }

    result1 = compute_dataset_id(inputs_meta1)
    result2 = compute_dataset_id(inputs_meta2)

    # Should produce same hash because inputs are sorted alphabetically
    assert result1 == result2


def test_compute_dataset_id_canonical_form():
    """Test that canonical form uses tabs and newlines correctly."""
    inputs_meta = {
        "samples": {
            "sha256": "a" * 64,
            "n_rows": 10,
            "n_cols": 5,
        }
    }

    result = compute_dataset_id(inputs_meta)

    # Manually compute expected hash to verify canonical form
    canonical_line = f"samples\t{'a' * 64}\t10\t5"
    expected_hash = sha256(canonical_line.encode("utf-8")).hexdigest()
    expected_result = f"sha256:{expected_hash}"

    assert result == expected_result


def test_compute_dataset_id_multiple_inputs_canonical_form():
    """Test canonical form with multiple inputs (sorted alphabetically)."""
    inputs_meta = {
        "files": {
            "sha256": "b" * 64,
            "n_rows": 3,
            "n_cols": 3,
        },
        "samples": {
            "sha256": "a" * 64,
            "n_rows": 10,
            "n_cols": 5,
        },
    }

    result = compute_dataset_id(inputs_meta)

    # Manually compute expected hash (files comes before samples alphabetically)
    line1 = f"files\t{'b' * 64}\t3\t3"
    line2 = f"samples\t{'a' * 64}\t10\t5"
    canonical_string = "\n".join([line1, line2])
    expected_hash = sha256(canonical_string.encode("utf-8")).hexdigest()
    expected_result = f"sha256:{expected_hash}"

    assert result == expected_result


def test_compute_dataset_id_missing_sha256_with_path(tmp_path):
    """Test that sha256 is computed automatically from path if missing."""
    # Create a test file
    test_file = tmp_path / "test.txt"
    test_file.write_text("test content", encoding="utf-8")

    # Compute expected sha256
    from fairy.core.services.provenance import sha256_file

    expected_sha256 = sha256_file(test_file)

    inputs_meta = {
        "samples": {
            "path": str(test_file),
            "n_rows": 10,
            "n_cols": 5,
            # sha256 is missing, should be computed from path
        }
    }

    result = compute_dataset_id(inputs_meta)

    # Verify it worked by checking the hash includes the computed sha256
    # The result should be deterministic based on the file content
    assert result.startswith("sha256:")

    # Verify it's the same as if we provided sha256 directly
    inputs_meta_with_sha256 = {
        "samples": {
            "sha256": expected_sha256,
            "n_rows": 10,
            "n_cols": 5,
        }
    }
    result2 = compute_dataset_id(inputs_meta_with_sha256)
    assert result == result2


def test_compute_dataset_id_missing_sha256_no_path():
    """Test that missing sha256 without path raises ValueError."""
    inputs_meta = {
        "samples": {
            "n_rows": 10,
            "n_cols": 5,
            # sha256 and path both missing
        }
    }

    with pytest.raises(ValueError, match="lacks sha256 and no path available"):
        compute_dataset_id(inputs_meta)


def test_compute_dataset_id_missing_sha256_nonexistent_path():
    """Test that missing sha256 with nonexistent path raises FileNotFoundError."""
    inputs_meta = {
        "samples": {
            "path": "/nonexistent/path/to/file.txt",
            "n_rows": 10,
            "n_cols": 5,
        }
    }

    with pytest.raises((FileNotFoundError, ValueError)) as exc_info:
        compute_dataset_id(inputs_meta)
    # Should raise either FileNotFoundError or ValueError with helpful message
    assert (
        "nonexistent" in str(exc_info.value).lower()
        or "does not exist" in str(exc_info.value).lower()
    )


def test_compute_dataset_id_missing_n_rows():
    """Test that missing n_rows raises ValueError."""
    inputs_meta = {
        "samples": {
            "sha256": "a" * 64,
            "n_cols": 5,
            # n_rows missing
        }
    }

    with pytest.raises(ValueError, match="lacks n_rows or n_cols"):
        compute_dataset_id(inputs_meta)


def test_compute_dataset_id_missing_n_cols():
    """Test that missing n_cols raises ValueError."""
    inputs_meta = {
        "samples": {
            "sha256": "a" * 64,
            "n_rows": 10,
            # n_cols missing
        }
    }

    with pytest.raises(ValueError, match="lacks n_rows or n_cols"):
        compute_dataset_id(inputs_meta)


def test_compute_dataset_id_utf8_handling():
    """Test that UTF-8 input names are handled correctly."""
    inputs_meta = {
        "samples_测试": {  # Chinese characters
            "sha256": "a" * 64,
            "n_rows": 10,
            "n_cols": 5,
        }
    }

    result = compute_dataset_id(inputs_meta)
    assert result.startswith("sha256:")
    assert len(result) == 7 + 64


def test_compute_dataset_id_zero_rows_cols():
    """Test that zero rows/cols are handled correctly."""
    inputs_meta = {
        "samples": {
            "sha256": "a" * 64,
            "n_rows": 0,
            "n_cols": 0,
        }
    }

    result = compute_dataset_id(inputs_meta)
    assert result.startswith("sha256:")

    # Verify canonical form includes zeros
    canonical_line = f"samples\t{'a' * 64}\t0\t0"
    expected_hash = sha256(canonical_line.encode("utf-8")).hexdigest()
    expected_result = f"sha256:{expected_hash}"
    assert result == expected_result
