def test_config_has_six_departments_each_with_required_fields(cfg):
    assert len(cfg["departments"]) == 6
    assert all(d["required_fields"] for d in cfg["departments"].values())


def test_config_shape(cfg):
    assert cfg["today"] == "2026-11-10"
    assert len(cfg["sources"]) == 6 and len(cfg["types"]) == 8
    assert len(cfg["bank_holidays"]) == 16
    assert {p["kind"] for p in cfg["paths"]} == {"normal", "urgent", "returned", "second_return"}


def test_data_sources_are_public_sources_with_a_link_and_our_assumptions(cfg):
    pub, own = cfg["data_sources"]["public"], cfg["data_sources"]["assumptions"]
    assert len(pub) == 7 and all(set(d) == {"follows", "source", "date", "url"} for d in pub)
    assert all(d["url"].startswith("https://") and "handbook.fca.org.uk" not in d["url"] for d in pub)  # the Handbook pages were not verified
    assert [a["what"] for a in own] == ["Channel mix", "Hour-of-day pattern", "Volume ramp", "Return rate", "Handover field list", "Open share"]
