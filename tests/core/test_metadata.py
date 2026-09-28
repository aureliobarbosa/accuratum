from accuratum.core.metadata import selector_matches


def test_selector_matches_subset():
    metadata = {"kind": "hourline", "hour": 6, "minute": 0}
    assert selector_matches({"kind": "hourline", "hour": 6}, metadata)
    assert selector_matches({"hour": 6}, metadata)
    assert selector_matches({}, metadata)


def test_selector_rejects_wrong_value():
    metadata = {"kind": "hourline", "hour": 6}
    assert not selector_matches({"hour": 7}, metadata)
    assert not selector_matches({"kind": "dayline"}, metadata)


def test_selector_rejects_extra_key():
    metadata = {"kind": "hourline"}
    assert not selector_matches({"kind": "hourline", "hour": 6}, metadata)
