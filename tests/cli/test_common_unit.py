from pathlib import Path

from fairy.cli.common import parse_inputs_kv, resolve_input_path, sha256_bytes


def test_parse_inputs_kv_ok():
    got = parse_inputs_kv(["a=./x.csv", "b= y.txt "])
    assert got == {"a": "./x.csv", "b": "y.txt"}


def test_parse_inputs_kv_bad():
    try:
        parse_inputs_kv(["noequals"])
        raise AssertionError("expected SystemExit")
    except SystemExit:
        pass


def test_resolve_input_path_file(tmp_path: Path):
    p = tmp_path / "file.csv"
    p.write_text("a\n1\n", encoding="utf-8")
    assert resolve_input_path(p) == p


def test_sha256_bytes_roundtrip():
    h = sha256_bytes(b"abc")
    assert len(h) == 64 and h.isalnum()
