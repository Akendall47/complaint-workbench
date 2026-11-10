from workbench.handover import missing_fields


def test_missing_in_config_order(cfg):
    h = {"amount_disputed": "10 pounds", "merchant_name": "  ", "card_last_four": None}
    assert missing_fields("Fraud claims", h, cfg) == ["date_of_transaction", "merchant_name", "card_last_four", "police_reference"]


def test_complete(cfg):
    h = {f: "x" for f in cfg["departments"]["Bereavement"]["required_fields"]}
    assert missing_fields("Bereavement", h, cfg) == []


def test_extra_keys_ignored(cfg):
    assert missing_fields("Data protection", {"other": "x"}, cfg) == cfg["departments"]["Data protection"]["required_fields"]
