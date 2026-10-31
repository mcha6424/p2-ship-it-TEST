"""The golden set: tickets with the right answer attached, tagged by slice. Lives in data/golden/."""
from __future__ import annotations

import json
from pathlib import Path

GOLDEN = Path("data/golden/golden.json")
ACCOUNTS = Path("data/golden/accounts.json")


def load_golden(path: Path = GOLDEN) -> list[dict]:
    items = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(items, list), "dataset must be a JSON array of tickets"
    ids = [i["id"] for i in items]
    assert len(ids) == len(set(ids)), "duplicate id in dataset"
    return items


def load_accounts(path: Path = ACCOUNTS) -> dict[str, dict]:
    return json.loads(path.read_text(encoding="utf-8"))


def tags(item: dict) -> list[str]:
    """Every slice an item belongs to. 'all' is every item; 'ambiguous' is a slice too."""
    return ["all"] + item["slices"] + (["ambiguous"] if item.get("ambiguous") else [])
