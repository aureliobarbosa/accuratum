"""Smoke test — verifies the package is importable and the CLI runs end-to-end."""


def test_imports():
    import accuratum.cli  # noqa: F401
    import accuratum.core.builder  # noqa: F401
    import accuratum.core.spec  # noqa: F401
    import accuratum.location  # noqa: F401
    import accuratum.projections.accuratum  # noqa: F401
    import accuratum.renderers.matplotlib_backend  # noqa: F401


def test_cli_produces_output(tmp_path, monkeypatch):
    from accuratum.cli import main

    monkeypatch.chdir(tmp_path)

    out = tmp_path / "smoke.png"
    exit_code = main(
        [
            "--lat-long=0,0",
            "--output",
            str(out),
            "--line-points",
            "20",
            "--time-step",
            "120",
            "--dayline-day-step",
            "30",
            "--hourline-day-step",
            "30",
        ]
    )

    assert exit_code == 0
    assert out.exists()
    assert out.stat().st_size > 0
