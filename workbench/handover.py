def missing_fields(department: str, handover: dict, cfg: dict) -> list[str]:
    def blank(v):
        return v is None or not str(v).strip()
    return [f for f in cfg["departments"][department]["required_fields"] if blank(handover.get(f))]
