import sys

from fairy.cli.__main__ import main


def test_main_prints_help_on_no_args(monkeypatch, capsys):
    # no args → prints help and exits 2
    monkeypatch.setattr(sys, "argv", ["fairy"])
    rc = main([])
    out = capsys.readouterr().out + capsys.readouterr().err
    assert rc == 2
    assert "FAIRy CLI" in out


def test_main_top_level_version(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["fairy", "--version"])
    rc = main([])
    out = capsys.readouterr().out
    assert rc == 0
    assert "fairy " in out
