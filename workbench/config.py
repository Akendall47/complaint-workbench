from pathlib import Path

import yaml


def load_config(path: str | Path = "config/pipeline.yaml") -> dict:
    cfg = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    # YAML parses bare dates to date objects; the rest of the code uses ISO strings.
    cfg["today"] = str(cfg["today"])
    cfg["bank_holidays"] = [str(d) for d in cfg["bank_holidays"]]
    return cfg
