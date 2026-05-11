"""Smoke test — verifies the package is importable and the CLI runs end-to-end."""


def test_imports():
    import accuratum.astronomy  # noqa: F401
    import accuratum.cli  # noqa: F401
    import accuratum.datetime_utils  # noqa: F401
    import accuratum.graph  # noqa: F401
    import accuratum.location  # noqa: F401


def test_cli_produces_output(tmp_path):
    from accuratum.cli import main

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
