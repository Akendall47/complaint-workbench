def test_config_has_six_departments_each_with_required_fields(cfg):
    assert len(cfg["departments"]) == 6
    assert all(d["required_fields"] for d in cfg["departments"].values())


def test_config_shape(cfg):
    assert cfg["today"] == "2026-11-10"
    assert len(cfg["sources"]) == 6 and len(cfg["types"]) == 8
    assert len(cfg["bank_holidays"]) == 16
    assert len(cfg["data_sources"]) == 6
    assert {p["kind"] for p in cfg["paths"]} == {"normal", "urgent", "returned", "second_return"}
