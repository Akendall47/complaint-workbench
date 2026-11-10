def test_config_has_six_departments_each_with_required_fields(cfg):
    assert len(cfg["departments"]) == 6
    assert all(d["required_fields"] for d in cfg["departments"].values())


def test_config_shape(cfg):
    assert cfg["today"] == "2026-11-10"
    assert len(cfg["sources"]) == 6 and len(cfg["types"]) == 8
    assert len(cfg["bank_holidays"]) == 16
    assert len(cfg["data_sources"]) == 6
    assert {p["kind"] for p in cfg["paths"]} == {"normal", "urgent", "returned", "second_return"}


def test_data_sources_names_in_order(cfg):
    assert [d["data"] for d in cfg["data_sources"]] == [
        "Cases and case notes", "Case events and deadlines", "Policy documents",
        "AI summaries", "Audit log", "Staff"]
    assert all(set(d) == {"data", "prototype", "real_bank", "personal_data", "refresh"} for d in cfg["data_sources"])
